"""
main.py — Orchestrator for the Live Stock & Crypto Market Intelligence System.

Wires together all pipeline modules:
  1. Market data ingestion (simulated streaming)
  2. News ingestion (CSV directory watcher)
  3. Financial indicator computation
  4. Market regime detection
  5. Anomaly detection
  6. Portfolio risk engine
  7. Correlation engine
  8. RAG document store
  9. AI explanations & market narrator

Exposes:
  - FastAPI REST server with all endpoints
  - WebSocket endpoint for real-time browser updates
  - Static file serving for the frontend dashboard
  - Structured logging
"""

import asyncio
import threading
import time
import json
import logging
import os
import sys
import csv
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from pathlib import Path

import config
from streaming_engine import engine, StreamTable
from ingestion import create_market_stream, create_news_stream
from indicators import compute_indicators
from regime_detection import classify_regime
from anomaly_detection import detect_anomalies
from portfolio_engine import compute_portfolio_metrics
from correlation_engine import correlation_tracker
from rag_module import doc_store, index_news_from_table_callback
from ai_explanations import (
    ask_market_question,
    explain_anomaly,
    generate_market_narrative,
    get_latest_narrative,
)
from websocket_manager import ws_manager

# ═══════════════════════════════════════════════════════════
#  LOGGING
# ═══════════════════════════════════════════════════════════

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format=config.LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("market_intelligence.log", mode="a"),
    ],
)
logger = logging.getLogger("main")

# ═══════════════════════════════════════════════════════════
#  SHARED STATE (updated by pipeline callbacks)
# ═══════════════════════════════════════════════════════════

class MarketState:
    """Thread-safe market state container updated by the streaming pipeline."""

    def __init__(self):
        self._lock = threading.Lock()
        self.indicators: dict[str, dict] = {}
        self.regimes: dict[str, str] = {}
        self.anomalies: dict[str, dict] = {}
        self.portfolio: dict[str, dict] = {}
        self.portfolio_summary: dict = {}
        self.correlations: list[dict] = []
        self.tick_count: int = 0
        self.start_time: str = datetime.now(timezone.utc).isoformat()
        self._indicator_states: dict[str, str] = {}
        self._regime_states: dict[str, str] = {}
        self._anomaly_states: dict[str, str] = {}
        self._portfolio_states: dict[str, str] = {}

    def update_tick(self, symbol: str, price: float, volume: float, timestamp: int):
        """Process a new tick through all pipeline stages."""
        with self._lock:
            self.tick_count += 1

            # ── 1. Compute Indicators ──
            ind_state = self._indicator_states.get(symbol)
            ind_result = compute_indicators(symbol, price, volume, timestamp, ind_state)
            ind_parsed = json.loads(str(ind_result))
            ind_data = ind_parsed["indicators"]
            self._indicator_states[symbol] = ind_parsed["state"]
            self.indicators[symbol] = ind_data

            # ── 2. Detect Regime ──
            regime_state = self._regime_states.get(symbol)
            regime_result = classify_regime(
                symbol, price,
                ind_data.get("sma_short", price),
                ind_data.get("sma_long", price),
                ind_data.get("sma_slope", 0),
                ind_data.get("rolling_vol", 0),
                ind_data.get("rsi", 50),
                regime_state,
            )
            regime_parsed = json.loads(str(regime_result))
            self.regimes[symbol] = regime_parsed.get("regime", "UNKNOWN")
            self._regime_states[symbol] = regime_parsed.get("_state", "")
            self.indicators[symbol]["regime"] = self.regimes[symbol]
            self.indicators[symbol]["regime_confidence"] = regime_parsed.get("confidence", 0)
            self.indicators[symbol]["regime_changed"] = regime_parsed.get("regime_changed", False)

            # Broadcast regime via WS
            if regime_parsed.get("regime_changed"):
                ws_manager.broadcast("regime", {
                    "symbol": symbol,
                    "regime": self.regimes[symbol],
                    "previous": regime_parsed.get("previous_regime"),
                })

            # ── 3. Detect Anomalies ──
            anom_state = self._anomaly_states.get(symbol)
            anom_result = detect_anomalies(
                symbol, price, volume,
                ind_data.get("rolling_vol", 0),
                ind_data.get("vol_avg", volume),
                timestamp, anom_state,
            )
            anom_parsed = json.loads(str(anom_result))
            self.anomalies[symbol] = anom_parsed
            self._anomaly_states[symbol] = anom_parsed.get("_state", "")

            # Broadcast alerts via WS
            if anom_parsed.get("has_anomaly"):
                ws_manager.broadcast("alert", {
                    "symbol": symbol,
                    "alerts": anom_parsed.get("alerts", []),
                    "max_severity": anom_parsed.get("max_severity"),
                })

            # ── 4. Update Correlation Tracker ──
            correlation_tracker.update(symbol, price)

            # ── 5. Broadcast tick via WS ──
            ws_manager.broadcast("tick", ind_data)

            # Log periodically
            if self.tick_count % 25 == 0:
                logger.info(
                    f"📊 Tick #{self.tick_count} | {symbol}=${price:.2f} | "
                    f"Regime={self.regimes[symbol]} | RSI={ind_data.get('rsi', 'N/A')} | "
                    f"WS clients={ws_manager.client_count}"
                )

    def update_portfolio(self, symbol: str, quantity: float, avg_cost: float,
                         current_price: float, rolling_vol: float):
        """Update portfolio metrics for a position."""
        with self._lock:
            port_state = self._portfolio_states.get(symbol)
            result = compute_portfolio_metrics(
                symbol, quantity, avg_cost, current_price, rolling_vol, port_state,
            )
            parsed = json.loads(str(result))
            self.portfolio[symbol] = parsed
            self._portfolio_states[symbol] = parsed.get("_state", "")

    def compute_portfolio_summary(self):
        """Aggregate portfolio metrics."""
        with self._lock:
            if not self.portfolio:
                return
            total_value = sum(p.get("market_value", 0) for p in self.portfolio.values())
            total_cost = sum(p.get("cost_basis", 0) for p in self.portfolio.values())
            total_pnl = sum(p.get("pnl", 0) for p in self.portfolio.values())
            total_var = sum(p.get("var_95", 0) for p in self.portfolio.values())
            avg_risk = sum(p.get("risk_score", 0) for p in self.portfolio.values()) / max(len(self.portfolio), 1)
            max_dd = max((p.get("drawdown_pct", 0) for p in self.portfolio.values()), default=0)

            self.portfolio_summary = {
                "total_value": round(total_value, 2),
                "total_cost": round(total_cost, 2),
                "total_pnl": round(total_pnl, 2),
                "total_pnl_pct": round((total_pnl / total_cost * 100) if total_cost > 0 else 0, 2),
                "total_var_95": round(total_var, 2),
                "avg_risk_score": round(avg_risk, 1),
                "max_drawdown_pct": round(max_dd, 2),
                "positions": len(self.portfolio),
            }

    def update_correlations(self):
        with self._lock:
            self.correlations = correlation_tracker.compute_all_pairs()

    def get_market_context(self) -> dict:
        with self._lock:
            return {
                "indicators": dict(self.indicators),
                "regimes": dict(self.regimes),
                "anomalies": dict(self.anomalies),
                "portfolio": dict(self.portfolio_summary),
            }

    def get_status(self) -> dict:
        return {
            "status": "running",
            "tick_count": self.tick_count,
            "start_time": self.start_time,
            "assets_tracked": list(self.indicators.keys()),
            "news_indexed": doc_store.doc_count,
            "ws_clients": ws_manager.client_count,
            "uptime_seconds": int(time.time() - datetime.fromisoformat(self.start_time).timestamp()),
        }


# Global state
state = MarketState()


# ═══════════════════════════════════════════════════════════
#  STREAMING CALLBACKS
# ═══════════════════════════════════════════════════════════

_portfolio_positions_cache = None

def _get_portfolio_positions() -> dict:
    global _portfolio_positions_cache
    if _portfolio_positions_cache is not None:
        return _portfolio_positions_cache
    positions = {}
    try:
        with open(config.PORTFOLIO_CSV, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                positions[row["symbol"]] = {
                    "quantity": float(row["quantity"]),
                    "avg_cost": float(row["avg_cost"]),
                }
        logger.info(f"💼 Loaded {len(positions)} portfolio positions")
    except FileNotFoundError:
        logger.warning("No portfolio.csv found")
    except Exception as e:
        logger.error(f"Error loading portfolio: {e}")
    _portfolio_positions_cache = positions
    return positions


def on_market_tick(key, row, time_val, is_addition):
    """Callback for each market tick from the stream."""
    if not is_addition:
        return

    symbol = row.get("symbol", "")
    price = float(row.get("price", 0.0))
    volume = float(row.get("volume", 0.0))
    timestamp = int(row.get("timestamp", 0))

    # Process through full pipeline
    state.update_tick(symbol, price, volume, timestamp)

    # Update portfolio
    portfolio_positions = _get_portfolio_positions()
    if symbol in portfolio_positions:
        pos = portfolio_positions[symbol]
        ind = state.indicators.get(symbol, {})
        state.update_portfolio(
            symbol, pos["quantity"], pos["avg_cost"],
            price, ind.get("rolling_vol", 0.02),
        )
        state.compute_portfolio_summary()

    # Update correlations every 10 ticks
    if state.tick_count % 10 == 0:
        state.update_correlations()
        ws_manager.broadcast("correlation", state.correlations)

    # Broadcast portfolio every 5 ticks
    if state.tick_count % 5 == 0 and state.portfolio_summary:
        ws_manager.broadcast("portfolio", {
            "summary": state.portfolio_summary,
            "positions": state.portfolio,
        })


def on_news_article(key, row, time_val, is_addition):
    """Callback for each news article from the stream."""
    if not is_addition:
        return
    index_news_from_table_callback(row)


# ═══════════════════════════════════════════════════════════
#  NARRATOR BACKGROUND THREAD
# ═══════════════════════════════════════════════════════════

def _narrator_loop():
    logger.info(f"📝 Market narrator started (interval={config.NARRATOR_INTERVAL_SECONDS}s)")
    time.sleep(30)
    while True:
        try:
            ctx = state.get_market_context()
            generate_market_narrative(ctx)
            narrative = get_latest_narrative()
            ws_manager.broadcast("narrator", narrative)
        except Exception as e:
            logger.error(f"Narrator error: {e}")
        time.sleep(config.NARRATOR_INTERVAL_SECONDS)


# ═══════════════════════════════════════════════════════════
#  FASTAPI APPLICATION
# ═══════════════════════════════════════════════════════════

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn


class AskRequest(BaseModel):
    question: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Capture the event loop for WebSocket broadcasting from background threads
    loop = asyncio.get_event_loop()
    ws_manager.set_event_loop(loop)
    logger.info(f"🌐 REST API + WebSocket server ready on http://{config.API_HOST}:{config.API_PORT}")
    yield
    logger.info("Server shutting down")


app = FastAPI(
    title="Market Intelligence System",
    description="Real-time Stock & Crypto Market Intelligence with AI",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── WebSocket Endpoint ───────────────────────────

@app.websocket("/ws/market")
async def websocket_endpoint(websocket: WebSocket):
    """Real-time streaming endpoint for browser clients."""
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive — client can send ping or commands
            data = await websocket.receive_text()
            # Handle client messages (e.g., subscribe to specific symbols)
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)


# ─── Frontend Serving ─────────────────────────────

FRONTEND_DIR = Path(__file__).parent / "frontend"

@app.get("/")
def serve_dashboard():
    """Serve the main dashboard."""
    return FileResponse(FRONTEND_DIR / "index.html")


# ─── REST API Endpoints ──────────────────────────

@app.get("/api/status")
def get_status():
    return state.get_status()


@app.get("/api/indicators")
def get_indicators(symbol: str = Query(None)):
    if symbol:
        data = state.indicators.get(symbol.upper())
        if data:
            return {"symbol": symbol.upper(), "indicators": data}
        return JSONResponse(status_code=404, content={"error": f"Symbol {symbol} not found"})
    return {"assets": state.indicators, "count": len(state.indicators)}


@app.get("/api/regimes")
def get_regimes(symbol: str = Query(None)):
    if symbol:
        regime = state.regimes.get(symbol.upper())
        if regime:
            return {"symbol": symbol.upper(), "regime": regime}
        return JSONResponse(status_code=404, content={"error": f"Symbol {symbol} not found"})
    return {"regimes": state.regimes, "count": len(state.regimes)}


@app.get("/api/anomalies")
def get_anomalies(symbol: str = Query(None), severity: str = Query(None)):
    anomalies = state.anomalies
    if symbol:
        data = anomalies.get(symbol.upper())
        if data:
            return {"symbol": symbol.upper(), "anomalies": data}
        return JSONResponse(status_code=404, content={"error": f"Symbol {symbol} not found"})
    if severity:
        filtered = {
            s: a for s, a in anomalies.items()
            if isinstance(a, dict) and a.get("max_severity", "").upper() == severity.upper()
        }
        return {"anomalies": filtered, "count": len(filtered)}
    return {"anomalies": anomalies, "count": len(anomalies)}


@app.get("/api/portfolio")
def get_portfolio():
    return {
        "summary": state.portfolio_summary,
        "positions": state.portfolio,
        "position_count": len(state.portfolio),
    }


@app.get("/api/correlations")
def get_correlations():
    return {
        "correlations": state.correlations,
        "pairs": [f"{a}-{b}" for a, b in config.CORRELATION_PAIRS],
    }


@app.get("/api/narrator")
def get_narrator():
    return get_latest_narrative()


@app.post("/api/ask")
def ask_question(req: AskRequest):
    ctx = state.get_market_context()
    return ask_market_question(req.question, ctx)


@app.get("/api/anomalies/explain")
def explain_anomaly_endpoint(symbol: str):
    anom = state.anomalies.get(symbol.upper())
    if not anom:
        return JSONResponse(status_code=404, content={"error": f"No anomaly data for {symbol}"})
    ctx = state.get_market_context()
    explanation = explain_anomaly(anom, ctx)
    return {"symbol": symbol.upper(), "explanation": explanation}


@app.get("/health")
def health_check():
    return {"status": "healthy", "uptime": state.get_status().get("uptime_seconds", 0)}


# Mount static files LAST so API routes take priority
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


# ═══════════════════════════════════════════════════════════
#  PIPELINE SETUP & RUN
# ═══════════════════════════════════════════════════════════

def start_api_server():
    uvicorn.run(app, host=config.API_HOST, port=config.API_PORT, log_level="warning")


def run_pipeline():
    logger.info("=" * 70)
    logger.info("  LIVE STOCK & CRYPTO MARKET INTELLIGENCE SYSTEM  v2.0")
    logger.info("  Streaming Engine + FastAPI + WebSocket + AI Dashboard")
    logger.info("=" * 70)

    os.makedirs(config.NEWS_DIR, exist_ok=True)
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    # ── 1. Create streams ──
    logger.info("📡 Setting up data streams...")
    market_data = create_market_stream()
    news_data = create_news_stream()

    # ── 2. Subscribe callbacks ──
    market_data.subscribe(on_market_tick, replay_existing=False)
    news_data.subscribe(on_news_article)

    # ── 3. JSONL sinks ──
    market_data.add_jsonl_sink(os.path.join(config.OUTPUT_DIR, "market_ticks.jsonl"))
    news_data.add_jsonl_sink(os.path.join(config.OUTPUT_DIR, "news_articles.jsonl"))

    # ── 4. Register with engine ──
    engine.register(market_data)
    engine.register(news_data)

    # ── 5. Start FastAPI server ──
    api_thread = threading.Thread(target=start_api_server, daemon=True)
    api_thread.start()
    logger.info(f"🌐 Dashboard:  http://localhost:{config.API_PORT}")
    logger.info(f"🔌 WebSocket:  ws://localhost:{config.API_PORT}/ws/market")

    # ── 6. Start narrator ──
    narrator_thread = threading.Thread(target=_narrator_loop, daemon=True)
    narrator_thread.start()

    # ── 7. Run engine (blocks) ──
    logger.info("🚀 Starting streaming engine...")
    logger.info(f"   Assets: {config.ASSETS}")
    logger.info(f"   Tick interval: {config.TICK_INTERVAL_SECONDS}s")
    logger.info(f"   News directory: {config.NEWS_DIR}")
    logger.info("   Press Ctrl+C to stop.")
    logger.info("=" * 70)

    try:
        engine.run()
    except KeyboardInterrupt:
        logger.info("\n🛑 Shutting down gracefully...")
    except Exception as e:
        logger.error(f"Pipeline error: {e}")
        raise


if __name__ == "__main__":
    run_pipeline()
