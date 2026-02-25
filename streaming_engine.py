"""
streaming_engine.py — Cross-platform streaming engine for the Market Intelligence System.

Provides Pathway-compatible streaming abstractions that work natively on Windows:
  - StreamTable: analogous to pw.Table
  - ConnectorSubject: background data generator
  - CSV directory watcher (streaming mode)
  - subscribe() for on_change callbacks
  - run() to start the engine loop

This module is the single compatibility layer. All other modules use
Pathway-style UDFs (@pw.udf decorator) through this engine.
When deploying on Linux, this can be swapped for native Pathway connectors.
"""

import threading
import time
import os
import csv
import json
import logging
import queue
from datetime import datetime, timezone
from typing import Callable, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
#  STREAMING TABLE
# ═══════════════════════════════════════════════════════════

@dataclass
class StreamRecord:
    """A single record in a stream."""
    data: dict
    timestamp: float = field(default_factory=time.time)
    is_addition: bool = True


class StreamTable:
    """
    A streaming table analogous to pw.Table.
    Supports subscribing to new records and writing to JSONL sinks.
    Thread-safe for concurrent producers and consumers.
    """

    def __init__(self, name: str, schema: dict = None):
        self.name = name
        self.schema = schema or {}
        self._subscribers: list[Callable] = []
        self._records: list[StreamRecord] = []
        self._lock = threading.Lock()
        self._jsonl_sinks: list[str] = []

    def emit(self, record: dict):
        """Emit a new record into the stream."""
        sr = StreamRecord(data=record)
        with self._lock:
            self._records.append(sr)

        # Notify subscribers
        for callback in self._subscribers:
            try:
                callback(None, record, sr.timestamp, True)
            except Exception as e:
                logger.error(f"Subscriber error on {self.name}: {e}")

        # Write to JSONL sinks
        for sink_path in self._jsonl_sinks:
            try:
                with open(sink_path, "a") as f:
                    f.write(json.dumps(record, default=str) + "\n")
            except Exception as e:
                logger.error(f"JSONL write error: {e}")

    def subscribe(self, callback: Callable, replay_existing: bool = True):
        """Register a callback for new records: callback(key, row, time, is_addition).
        If replay_existing=True, replays all buffered records to the new subscriber."""
        self._subscribers.append(callback)
        if replay_existing:
            with self._lock:
                for sr in list(self._records):
                    try:
                        callback(None, sr.data, sr.timestamp, True)
                    except Exception as e:
                        logger.error(f"Replay error on {self.name}: {e}")

    def add_jsonl_sink(self, path: str):
        """Add a JSONL file sink."""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self._jsonl_sinks.append(path)

    @property
    def record_count(self) -> int:
        return len(self._records)


# ═══════════════════════════════════════════════════════════
#  CONNECTOR SUBJECT (Background Data Producer)
# ═══════════════════════════════════════════════════════════

class ConnectorSubject:
    """
    Base class for background data producers.
    Subclass and implement run() to generate data.
    Call self.next(**kwargs) to emit records.
    """

    def __init__(self):
        self._table: StreamTable | None = None
        self._thread: threading.Thread | None = None
        self.running: bool = True

    def next(self, **kwargs):
        """Emit a record to the connected stream table."""
        if self._table:
            self._table.emit(kwargs)

    def run(self):
        """Override this in subclass to generate data."""
        raise NotImplementedError

    def on_stop(self):
        """Override for cleanup."""
        self.running = False

    def _start(self, table: StreamTable):
        """Start the producer in a background thread."""
        self._table = table
        self._thread = threading.Thread(target=self._safe_run, daemon=True)
        self._thread.start()

    def _safe_run(self):
        try:
            self.run()
        except Exception as e:
            logger.error(f"ConnectorSubject error: {e}")


def read_python_connector(subject: ConnectorSubject, name: str = "python_stream") -> StreamTable:
    """Create a StreamTable fed by a ConnectorSubject. Analogous to pw.io.python.read()."""
    table = StreamTable(name=name)
    subject._start(table)
    return table


# ═══════════════════════════════════════════════════════════
#  CSV DIRECTORY WATCHER (Streaming Mode)
# ═══════════════════════════════════════════════════════════

class CSVDirectoryWatcher:
    """
    Watches a directory for CSV files and emits rows as stream records.
    Analogous to pw.io.csv.read(directory, mode="streaming").
    Tracks which files have been processed to avoid duplicates.
    """

    def __init__(self, directory: str, table: StreamTable, poll_interval: float = 5.0):
        self.directory = directory
        self.table = table
        self.poll_interval = poll_interval
        self._processed_files: set[str] = set()
        self._processed_mtimes: dict[str, float] = {}
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)

    def start(self):
        self._thread.start()
        logger.info(f"📂 CSV watcher started on: {self.directory}")

    def _watch_loop(self):
        while True:
            try:
                self._scan_directory()
            except Exception as e:
                logger.error(f"CSV watcher error: {e}")
            time.sleep(self.poll_interval)

    def _scan_directory(self):
        if not os.path.isdir(self.directory):
            return

        for filename in os.listdir(self.directory):
            if not filename.endswith(".csv"):
                continue

            filepath = os.path.join(self.directory, filename)
            mtime = os.path.getmtime(filepath)

            # Skip already-processed files with same mtime
            if filepath in self._processed_mtimes and self._processed_mtimes[filepath] == mtime:
                continue

            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    row_count = 0
                    for row in reader:
                        self.table.emit(dict(row))
                        row_count += 1
                self._processed_mtimes[filepath] = mtime
                logger.info(f"📰 Ingested {row_count} rows from {filename}")
            except Exception as e:
                logger.error(f"Error reading {filepath}: {e}")


def read_csv_directory(directory: str, name: str = "csv_stream", poll_interval: float = 5.0) -> StreamTable:
    """Create a StreamTable fed by CSV files in a directory. Analogous to pw.io.csv.read(mode='streaming')."""
    os.makedirs(directory, exist_ok=True)
    table = StreamTable(name=name)
    watcher = CSVDirectoryWatcher(directory, table, poll_interval)
    watcher.start()
    return table


def read_csv_static(filepath: str, name: str = "csv_static") -> list[dict]:
    """Read a single CSV file as static data. Analogous to pw.io.csv.read(mode='static')."""
    records = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(dict(row))
        logger.info(f"📄 Static CSV loaded: {filepath} ({len(records)} rows)")
    except FileNotFoundError:
        logger.warning(f"CSV file not found: {filepath}")
    except Exception as e:
        logger.error(f"Error reading CSV {filepath}: {e}")
    return records


# ═══════════════════════════════════════════════════════════
#  JSON / UDF HELPERS (pw.Json and @pw.udf compatibility)
# ═══════════════════════════════════════════════════════════

class JsonWrapper:
    """Lightweight JSON wrapper compatible with pw.Json interface."""

    def __init__(self, data):
        if isinstance(data, str):
            self._raw = data
        else:
            self._raw = json.dumps(data, default=str)

    def __str__(self):
        return self._raw

    def __repr__(self):
        return f"Json({self._raw[:80]}...)"


def udf(func):
    """
    Decorator compatible with @pw.udf.
    Makes functions callable with regular Python types while
    supporting JsonWrapper returns.
    """
    def wrapper(*args, **kwargs):
        # Convert any JsonWrapper args to strings for parsing
        converted_args = []
        for a in args:
            if isinstance(a, JsonWrapper):
                converted_args.append(str(a))
            else:
                converted_args.append(a)

        converted_kwargs = {}
        for k, v in kwargs.items():
            if isinstance(v, JsonWrapper):
                converted_kwargs[k] = str(v)
            else:
                converted_kwargs[k] = v

        return func(*converted_args, **converted_kwargs)
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


# ═══════════════════════════════════════════════════════════
#  ENGINE RUN
# ═══════════════════════════════════════════════════════════

class StreamingEngine:
    """
    The main streaming engine. Manages all tables and runs
    until interrupted. Analogous to pw.run().
    """

    def __init__(self):
        self.tables: list[StreamTable] = []
        self._running = False

    def register(self, table: StreamTable):
        self.tables.append(table)

    def run(self):
        """Block and keep the engine alive. All work happens in background threads."""
        self._running = True
        logger.info("🚀 Streaming engine started")
        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            self._running = False
            logger.info("🛑 Streaming engine stopped")

    def stop(self):
        self._running = False


# Global engine instance
engine = StreamingEngine()
