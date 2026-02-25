"""
indicators.py — Streaming financial indicator computations.

All computations are incremental and update automatically as new ticks arrive.

Computes:
  - SMA (Simple Moving Average) — short and long
  - EMA (Exponential Moving Average) — 12, 26 period
  - RSI (Relative Strength Index) — 14 period
  - MACD and Signal line
  - Bollinger Bands (upper, lower)
  - Rolling Volatility
"""

import logging
import json

import config
from streaming_engine import JsonWrapper, udf

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
#  STATEFUL INDICATOR UDF
# ═══════════════════════════════════════════════════════════

@udf
def compute_indicators(
    symbol: str,
    price: float,
    volume: float,
    timestamp: int,
    state: str | None,
) -> JsonWrapper:
    """
    Stateful UDF that maintains rolling windows and computes all indicators
    incrementally for each symbol. State is carried forward via the `state` param.
    """
    # Initialize state
    if state is None:
        s = {
            "prices": [],
            "volumes": [],
            "timestamps": [],
            "ema12": None,
            "ema26": None,
            "ema_signal": None,
            "avg_gain": 0.0,
            "avg_loss": 0.0,
            "count": 0,
        }
    else:
        try:
            s = json.loads(state)
        except (json.JSONDecodeError, TypeError):
            s = {
                "prices": [], "volumes": [], "timestamps": [],
                "ema12": None, "ema26": None, "ema_signal": None,
                "avg_gain": 0.0, "avg_loss": 0.0, "count": 0,
            }

    # Append current data
    s["prices"].append(price)
    s["volumes"].append(volume)
    s["timestamps"].append(timestamp)
    s["count"] += 1

    # Keep window bounded
    max_history = max(config.SMA_LONG_WINDOW, config.VOLATILITY_WINDOW, 60)
    if len(s["prices"]) > max_history:
        s["prices"] = s["prices"][-max_history:]
        s["volumes"] = s["volumes"][-max_history:]
        s["timestamps"] = s["timestamps"][-max_history:]

    prices = s["prices"]
    n = len(prices)

    # ── SMA ──
    sma_short = sum(prices[-config.SMA_SHORT_WINDOW:]) / min(n, config.SMA_SHORT_WINDOW)
    sma_long = sum(prices[-config.SMA_LONG_WINDOW:]) / min(n, config.SMA_LONG_WINDOW)

    # ── EMA ──
    def ema_update(prev_ema, price_val, span):
        k = 2.0 / (span + 1)
        if prev_ema is None:
            return price_val
        return price_val * k + prev_ema * (1 - k)

    s["ema12"] = ema_update(s["ema12"], price, config.EMA_SHORT_SPAN)
    s["ema26"] = ema_update(s["ema26"], price, config.EMA_LONG_SPAN)
    ema12 = s["ema12"]
    ema26 = s["ema26"]

    # ── MACD ──
    macd_line = ema12 - ema26
    s["ema_signal"] = ema_update(s["ema_signal"], macd_line, config.EMA_SIGNAL_SPAN)
    macd_signal = s["ema_signal"]
    macd_histogram = macd_line - macd_signal

    # ── RSI ──
    rsi = 50.0
    if n >= 2:
        change = prices[-1] - prices[-2]
        gain = max(change, 0)
        loss = abs(min(change, 0))

        period = config.RSI_PERIOD
        if s["count"] <= period:
            s["avg_gain"] = (s["avg_gain"] * (s["count"] - 1) + gain) / s["count"]
            s["avg_loss"] = (s["avg_loss"] * (s["count"] - 1) + loss) / s["count"]
        else:
            s["avg_gain"] = (s["avg_gain"] * (period - 1) + gain) / period
            s["avg_loss"] = (s["avg_loss"] * (period - 1) + loss) / period

        if s["avg_loss"] > 0:
            rs = s["avg_gain"] / s["avg_loss"]
            rsi = 100.0 - (100.0 / (1.0 + rs))
        elif s["avg_gain"] > 0:
            rsi = 100.0
        else:
            rsi = 50.0

    # ── Bollinger Bands ──
    bb_window = min(n, config.BOLLINGER_WINDOW)
    bb_prices = prices[-bb_window:]
    bb_mean = sum(bb_prices) / bb_window
    if bb_window > 1:
        bb_var = sum((p - bb_mean) ** 2 for p in bb_prices) / (bb_window - 1)
        bb_std = bb_var ** 0.5
    else:
        bb_std = 0.0
    bb_upper = bb_mean + config.BOLLINGER_STD_DEV * bb_std
    bb_lower = bb_mean - config.BOLLINGER_STD_DEV * bb_std

    # ── Rolling Volatility ──
    vol_window = min(n, config.VOLATILITY_WINDOW)
    if vol_window >= 2:
        returns = []
        vol_prices = prices[-vol_window:]
        for i in range(1, len(vol_prices)):
            if vol_prices[i - 1] > 0:
                returns.append((vol_prices[i] - vol_prices[i - 1]) / vol_prices[i - 1])
        if returns:
            mean_ret = sum(returns) / len(returns)
            var_ret = sum((r - mean_ret) ** 2 for r in returns) / len(returns)
            rolling_vol = var_ret ** 0.5
        else:
            rolling_vol = 0.0
    else:
        rolling_vol = 0.0

    # ── SMA Slope ──
    if n >= 3:
        prev_sma = sum(prices[-config.SMA_SHORT_WINDOW - 1:-1]) / min(n - 1, config.SMA_SHORT_WINDOW)
        sma_slope = (sma_short - prev_sma) / sma_short if sma_short != 0 else 0.0
    else:
        sma_slope = 0.0

    # ── Volume average ──
    vol_avg = sum(s["volumes"][-config.VOLATILITY_WINDOW:]) / min(n, config.VOLATILITY_WINDOW)

    result = {
        "symbol": symbol,
        "price": round(price, 4),
        "volume": round(volume, 2),
        "timestamp": timestamp,
        "sma_short": round(sma_short, 4),
        "sma_long": round(sma_long, 4),
        "sma_slope": round(sma_slope, 6),
        "ema12": round(ema12, 4),
        "ema26": round(ema26, 4),
        "macd_line": round(macd_line, 4),
        "macd_signal": round(macd_signal, 4),
        "macd_histogram": round(macd_histogram, 4),
        "rsi": round(rsi, 2),
        "bb_upper": round(bb_upper, 4),
        "bb_lower": round(bb_lower, 4),
        "bb_middle": round(bb_mean, 4),
        "rolling_vol": round(rolling_vol, 6),
        "vol_avg": round(vol_avg, 2),
        "data_points": n,
    }

    state_out = json.dumps(s)
    return JsonWrapper(json.dumps({"indicators": result, "state": state_out}))
