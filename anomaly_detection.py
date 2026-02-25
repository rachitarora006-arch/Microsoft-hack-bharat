"""
anomaly_detection.py — Real-time anomaly detection.

Detects:
  - Price spikes / drops (Z-score based)
  - Volume surges (vs rolling mean)
  - Volatility breakouts
  - Flash crash patterns (rapid large drops)

Generates structured alert objects with severity levels:
  LOW, MEDIUM, HIGH, EXTREME
"""

import logging
import json

import config
from streaming_engine import JsonWrapper, udf

logger = logging.getLogger(__name__)

SEVERITY_LOW = "LOW"
SEVERITY_MEDIUM = "MEDIUM"
SEVERITY_HIGH = "HIGH"
SEVERITY_EXTREME = "EXTREME"


@udf
def detect_anomalies(
    symbol: str,
    price: float,
    volume: float,
    rolling_vol: float,
    vol_avg: float,
    timestamp: int,
    state_json: str | None,
) -> JsonWrapper:
    """Stateful anomaly detector."""
    if state_json:
        try:
            s = json.loads(state_json)
        except (json.JSONDecodeError, TypeError):
            s = _init_state()
    else:
        s = _init_state()

    alerts = []

    s["price_history"].append(price)
    s["timestamp_history"].append(timestamp)

    max_hist = 100
    if len(s["price_history"]) > max_hist:
        s["price_history"] = s["price_history"][-max_hist:]
        s["timestamp_history"] = s["timestamp_history"][-max_hist:]

    prices = s["price_history"]
    n = len(prices)

    if n >= 3:
        mean_p = sum(prices) / n
        std_p = (sum((p - mean_p) ** 2 for p in prices) / n) ** 0.5

        # 1. Price Spike / Drop
        if std_p > 0:
            z_score = (price - mean_p) / std_p
            if abs(z_score) > config.PRICE_SPIKE_THRESHOLD:
                direction = "SPIKE" if z_score > 0 else "DROP"
                severity = _price_severity(abs(z_score))
                alerts.append({
                    "type": f"PRICE_{direction}",
                    "severity": severity,
                    "details": f"{direction}: Z={z_score:.2f}, Price={price:.2f}, Mean={mean_p:.2f}",
                })
                logger.warning(f"🚨 [{symbol}] PRICE {direction} (severity={severity})")

    # 2. Volume Surge
    if vol_avg > 0 and volume > config.VOLUME_SURGE_MULTIPLIER * vol_avg:
        ratio = volume / vol_avg
        severity = _volume_severity(ratio)
        alerts.append({
            "type": "VOLUME_SURGE",
            "severity": severity,
            "details": f"Volume={volume:.0f} is {ratio:.1f}x mean={vol_avg:.0f}",
        })
        logger.warning(f"🚨 [{symbol}] VOLUME SURGE {ratio:.1f}x (severity={severity})")

    # 3. Volatility Breakout
    baseline_vol = s.get("baseline_vol", rolling_vol)
    if baseline_vol > 0 and rolling_vol > config.VOL_BREAKOUT_THRESHOLD * baseline_vol:
        ratio = rolling_vol / baseline_vol
        severity = _vol_severity(ratio)
        alerts.append({
            "type": "VOLATILITY_BREAKOUT",
            "severity": severity,
            "details": f"Vol={rolling_vol:.6f} is {ratio:.1f}x baseline={baseline_vol:.6f}",
        })

    s["baseline_vol"] = 0.97 * s.get("baseline_vol", rolling_vol) + 0.03 * rolling_vol

    # 4. Flash Crash
    if n >= 2:
        timestamps = s["timestamp_history"]
        window_ms = config.FLASH_CRASH_WINDOW_SEC * 1000
        recent_max = price
        for i in range(len(prices) - 1, -1, -1):
            if timestamps[-1] - timestamps[i] > window_ms:
                break
            recent_max = max(recent_max, prices[i])

        if recent_max > 0:
            drop_pct = (recent_max - price) / recent_max
            if drop_pct > config.FLASH_CRASH_DROP_PCT:
                alerts.append({
                    "type": "FLASH_CRASH",
                    "severity": SEVERITY_EXTREME,
                    "details": f"Flash crash: {drop_pct:.1%} drop in {config.FLASH_CRASH_WINDOW_SEC}s. "
                              f"Peak={recent_max:.2f}→{price:.2f}",
                })
                logger.critical(f"💥 [{symbol}] FLASH CRASH: {drop_pct:.1%} drop!")

    result = {
        "symbol": symbol,
        "timestamp": timestamp,
        "alert_count": len(alerts),
        "alerts": alerts,
        "has_anomaly": len(alerts) > 0,
        "max_severity": _max_severity(alerts),
        "_state": json.dumps(s),
    }

    return JsonWrapper(json.dumps(result))


def _init_state():
    return {"price_history": [], "timestamp_history": [], "baseline_vol": 0.02}

def _price_severity(z):
    if z > 5.0: return SEVERITY_EXTREME
    if z > 4.0: return SEVERITY_HIGH
    if z > 3.0: return SEVERITY_MEDIUM
    return SEVERITY_LOW

def _volume_severity(ratio):
    if ratio > 10.0: return SEVERITY_EXTREME
    if ratio > 6.0: return SEVERITY_HIGH
    if ratio > 4.0: return SEVERITY_MEDIUM
    return SEVERITY_LOW

def _vol_severity(ratio):
    if ratio > 5.0: return SEVERITY_EXTREME
    if ratio > 3.5: return SEVERITY_HIGH
    if ratio > 2.5: return SEVERITY_MEDIUM
    return SEVERITY_LOW

def _max_severity(alerts):
    if not alerts: return "NONE"
    order = {SEVERITY_LOW: 1, SEVERITY_MEDIUM: 2, SEVERITY_HIGH: 3, SEVERITY_EXTREME: 4}
    return max(alerts, key=lambda a: order.get(a["severity"], 0))["severity"]
