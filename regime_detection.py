"""
regime_detection.py — Real-time market regime classification.

Classifies each asset into one of:
  - BULLISH   — SMA-short > SMA-long with positive slope
  - BEARISH   — SMA-short < SMA-long with negative slope
  - SIDEWAYS  — No clear trend
  - HIGH_VOLATILITY — Elevated volatility
  - CRASH     — Extreme volatility + sharp price drop
"""

import logging
import json

import config
from streaming_engine import JsonWrapper, udf

logger = logging.getLogger(__name__)

REGIMES = ["BULLISH", "BEARISH", "SIDEWAYS", "HIGH_VOLATILITY", "CRASH"]


@udf
def classify_regime(
    symbol: str,
    price: float,
    sma_short: float,
    sma_long: float,
    sma_slope: float,
    rolling_vol: float,
    rsi: float,
    state_json: str | None,
) -> JsonWrapper:
    """Classify market regime with shift detection."""
    prev_regime = "UNKNOWN"
    baseline_vol = 0.02
    price_history_min = price

    if state_json:
        try:
            prev = json.loads(state_json)
            prev_regime = prev.get("regime", "UNKNOWN")
            baseline_vol = prev.get("baseline_vol", 0.02)
            price_history_min = prev.get("recent_low", price)
        except (json.JSONDecodeError, TypeError):
            pass

    # Update baseline volatility (EMA smoothing)
    baseline_vol = 0.95 * baseline_vol + 0.05 * rolling_vol
    if baseline_vol < 1e-8:
        baseline_vol = 0.02

    vol_ratio = rolling_vol / baseline_vol if baseline_vol > 0 else 1.0
    recent_low = min(price_history_min, price)
    price_drop_pct = (sma_long - price) / sma_long if sma_long > 0 else 0

    # ── Classification ──
    if vol_ratio > config.REGIME_VOLATILITY_CRASH_MULT and price_drop_pct > config.REGIME_PRICE_DROP_CRASH:
        regime = "CRASH"
    elif vol_ratio > config.REGIME_VOLATILITY_HIGH_MULT:
        regime = "HIGH_VOLATILITY"
    elif sma_short > sma_long and sma_slope > config.REGIME_SMA_SLOPE_THRESHOLD:
        regime = "BULLISH"
    elif sma_short < sma_long and sma_slope < -config.REGIME_SMA_SLOPE_THRESHOLD:
        regime = "BEARISH"
    else:
        regime = "SIDEWAYS"

    regime_changed = regime != prev_regime and prev_regime != "UNKNOWN"
    if regime_changed:
        logger.warning(f"🔄 REGIME SHIFT [{symbol}]: {prev_regime} → {regime}")

    confidence = _regime_confidence(regime, vol_ratio, abs(sma_slope), rsi)

    result = {
        "symbol": symbol,
        "regime": regime,
        "previous_regime": prev_regime,
        "regime_changed": regime_changed,
        "vol_ratio": round(vol_ratio, 4),
        "price_drop_pct": round(price_drop_pct, 4),
        "sma_slope": round(sma_slope, 6),
        "rsi": round(rsi, 2),
        "confidence": confidence,
        "_state": json.dumps({
            "regime": regime,
            "baseline_vol": baseline_vol,
            "recent_low": recent_low,
        }),
    }

    return JsonWrapper(json.dumps(result))


def _regime_confidence(regime: str, vol_ratio: float, slope_abs: float, rsi: float) -> float:
    if regime == "CRASH":
        return min(1.0, vol_ratio / 5.0)
    elif regime == "HIGH_VOLATILITY":
        return min(1.0, vol_ratio / 4.0)
    elif regime == "BULLISH":
        return round(min(1.0, slope_abs * 100) * 0.5 + min(1.0, rsi / 100) * 0.5, 3)
    elif regime == "BEARISH":
        return round(min(1.0, slope_abs * 100) * 0.5 + min(1.0, (100 - rsi) / 100) * 0.5, 3)
    return 0.5
