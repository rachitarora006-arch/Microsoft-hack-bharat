"""
ingestion.py — Real-time data ingestion via streaming connectors.

Provides:
  - Simulated market tick stream (random-walk prices for BTC, ETH, SOL, NIFTY, SENSEX)
  - News article stream from CSV files in data/news/
"""

import time
import random
import logging
from datetime import datetime, timezone

import config
from streaming_engine import ConnectorSubject, read_python_connector, read_csv_directory, StreamTable

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
#  SIMULATED MARKET DATA GENERATOR
# ═══════════════════════════════════════════════════════════

class MarketDataGenerator:
    """
    Generates realistic random-walk tick data for configured assets.
    Injects occasional spikes/drops for anomaly detection testing.
    """

    def __init__(self):
        self.prices = dict(config.INITIAL_PRICES)
        self.volumes = dict(config.BASE_VOLUMES)

    def generate_tick(self, symbol: str) -> dict:
        """Generate a single tick with random-walk price movement."""
        vol = config.VOLATILITY_PROFILES.get(symbol, 0.02)

        # Per-tick volatility (√interval scaling)
        tick_vol = vol * (config.TICK_INTERVAL_SECONDS / 86400) ** 0.5

        # Random return with slight mean-reversion
        drift = random.gauss(0, tick_vol)

        # 1% chance of a spike/drop event (for anomaly testing)
        if random.random() < 0.01:
            drift += random.choice([-1, 1]) * random.uniform(0.02, 0.06)
            logger.info(f"⚡ Injecting price shock for {symbol}: {drift:+.4f}")

        new_price = self.prices[symbol] * (1 + drift)
        new_price = max(new_price, 0.01)
        self.prices[symbol] = new_price

        # Volume with random variation
        base_vol = self.volumes[symbol]
        volume = base_vol * random.uniform(0.5, 2.0)

        # Occasional volume surge
        if random.random() < 0.02:
            volume *= random.uniform(3.0, 8.0)
            logger.info(f"📊 Volume surge for {symbol}: {volume:.0f}")

        return {
            "symbol": symbol,
            "price": round(new_price, 4),
            "volume": round(volume, 2),
            "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
        }

    def generate_all_ticks(self) -> list[dict]:
        """Generate ticks for all assets."""
        return [self.generate_tick(s) for s in config.ASSETS]


# ═══════════════════════════════════════════════════════════
#  MARKET DATA STREAM
# ═══════════════════════════════════════════════════════════

class MarketSubject(ConnectorSubject):
    """Background subject emitting simulated market ticks."""

    def __init__(self):
        super().__init__()
        self.generator = MarketDataGenerator()

    def run(self):
        logger.info("🚀 Market data generator started")
        while self.running:
            ticks = self.generator.generate_all_ticks()
            for tick in ticks:
                self.next(**tick)
            time.sleep(config.TICK_INTERVAL_SECONDS)

    def on_stop(self):
        self.running = False
        logger.info("Market data generator stopped")


def create_market_stream() -> StreamTable:
    """Create a streaming table of market ticks."""
    subject = MarketSubject()
    table = read_python_connector(subject, name="market_data")
    logger.info(f"📡 Market stream created for assets: {config.ASSETS}")
    return table


# ═══════════════════════════════════════════════════════════
#  NEWS DATA STREAM
# ═══════════════════════════════════════════════════════════

def create_news_stream() -> StreamTable:
    """Create a streaming table from CSV files in the news directory."""
    import os
    os.makedirs(config.NEWS_DIR, exist_ok=True)
    table = read_csv_directory(config.NEWS_DIR, name="news_data", poll_interval=5.0)
    logger.info(f"📰 News stream watching: {config.NEWS_DIR}")
    return table
