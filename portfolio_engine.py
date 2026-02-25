"""
portfolio_engine.py — Real-time portfolio risk computation.

Reads user portfolio from CSV, joins with live market data, and computes:
  - Live P&L per position and total
  - Portfolio value
  - Max drawdown
  - Value at Risk (VaR) — parametric 95%
  - Composite risk score (0-100)
"""

import logging
import json

import config
from streaming_engine import JsonWrapper, udf, read_csv_static

logger = logging.getLogger(__name__)


@udf
def compute_portfolio_metrics(
    symbol: str,
    quantity: float,
    avg_cost: float,
    current_price: float,
    rolling_vol: float,
    state_json: str | None,
) -> JsonWrapper:
    """Compute portfolio metrics for a single position."""
    if state_json:
        try:
            s = json.loads(state_json)
        except (json.JSONDecodeError, TypeError):
            s = {"peak_value": 0.0}
    else:
        s = {"peak_value": 0.0}

    cost_basis = quantity * avg_cost
    market_value = quantity * current_price
    pnl = market_value - cost_basis
    pnl_pct = (pnl / cost_basis * 100) if cost_basis > 0 else 0.0

    s["peak_value"] = max(s.get("peak_value", market_value), market_value)
    peak = s["peak_value"]
    drawdown = (peak - market_value) / peak if peak > 0 else 0.0

    # VaR (parametric, 95%)
    z_95 = 1.645
    daily_vol = rolling_vol if rolling_vol > 0 else 0.02
    var_95 = market_value * daily_vol * z_95

    # Risk score (0-100)
    vol_score = min(40, daily_vol * 1000)
    drawdown_score = min(30, drawdown * 100)
    var_score = min(30, (var_95 / market_value * 100) if market_value > 0 else 0)
    risk_score = min(100, vol_score + drawdown_score + var_score)

    result = {
        "symbol": symbol,
        "quantity": quantity,
        "avg_cost": round(avg_cost, 2),
        "current_price": round(current_price, 4),
        "cost_basis": round(cost_basis, 2),
        "market_value": round(market_value, 2),
        "pnl": round(pnl, 2),
        "pnl_pct": round(pnl_pct, 2),
        "peak_value": round(peak, 2),
        "drawdown": round(drawdown, 4),
        "drawdown_pct": round(drawdown * 100, 2),
        "var_95": round(var_95, 2),
        "rolling_vol": round(daily_vol, 6),
        "risk_score": round(risk_score, 1),
        "_state": json.dumps(s),
    }

    return JsonWrapper(json.dumps(result))


def load_portfolio() -> list[dict]:
    """Load portfolio positions from CSV."""
    return read_csv_static(config.PORTFOLIO_CSV, name="portfolio")
