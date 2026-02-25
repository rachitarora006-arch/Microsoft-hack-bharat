"""
correlation_engine.py — Rolling cross-asset correlation via Pathway.

Computes Pearson correlation between configured asset pairs
(e.g., BTC-ETH, NIFTY-SENSEX) over a trailing window.

Alerts when correlation significantly breaks from recent history.
"""


import logging
import json
import math

import config

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
#  CORRELATION COMPUTATION
# ═══════════════════════════════════════════════════════════

class CorrelationTracker:
    """
    Maintains rolling price histories for asset pairs and computes
    Pearson correlation coefficient.
    """

    def __init__(self):
        self.histories: dict[str, list[float]] = {}
        self.prev_correlations: dict[str, float] = {}

    def update(self, symbol: str, price: float):
        """Record a new price for a symbol."""
        if symbol not in self.histories:
            self.histories[symbol] = []
        self.histories[symbol].append(price)

        # Cap history
        max_len = config.CORRELATION_WINDOW + 10
        if len(self.histories[symbol]) > max_len:
            self.histories[symbol] = self.histories[symbol][-max_len:]

    def compute_correlation(self, sym_a: str, sym_b: str) -> dict:
        """Compute Pearson correlation between two assets."""
        hist_a = self.histories.get(sym_a, [])
        hist_b = self.histories.get(sym_b, [])

        # Need at least window points from both
        min_len = min(len(hist_a), len(hist_b))
        if min_len < 5:
            return {
                "pair": f"{sym_a}-{sym_b}",
                "correlation": 0.0,
                "data_points": min_len,
                "sufficient_data": False,
                "alert": None,
            }

        window = min(min_len, config.CORRELATION_WINDOW)
        a = hist_a[-window:]
        b = hist_b[-window:]

        corr = self._pearson(a, b)

        # Check for correlation break
        pair_key = f"{sym_a}-{sym_b}"
        prev_corr = self.prev_correlations.get(pair_key, corr)
        change = abs(corr - prev_corr)
        self.prev_correlations[pair_key] = corr

        alert = None
        if change > config.CORRELATION_BREAK_THRESHOLD:
            alert = {
                "type": "CORRELATION_BREAK",
                "pair": pair_key,
                "previous": round(prev_corr, 4),
                "current": round(corr, 4),
                "change": round(change, 4),
                "severity": "HIGH" if change > 0.5 else "MEDIUM",
            }
            logger.warning(f"🔗 CORRELATION BREAK [{pair_key}]: {prev_corr:.3f} → {corr:.3f}")

        return {
            "pair": pair_key,
            "correlation": round(corr, 4),
            "previous_correlation": round(prev_corr, 4),
            "change": round(change, 4),
            "data_points": window,
            "sufficient_data": True,
            "alert": alert,
        }

    @staticmethod
    def _pearson(x: list[float], y: list[float]) -> float:
        """Compute Pearson correlation coefficient."""
        n = len(x)
        if n == 0:
            return 0.0

        mean_x = sum(x) / n
        mean_y = sum(y) / n

        cov = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n)) / n
        std_x = (sum((xi - mean_x) ** 2 for xi in x) / n) ** 0.5
        std_y = (sum((yi - mean_y) ** 2 for yi in y) / n) ** 0.5

        if std_x == 0 or std_y == 0:
            return 0.0

        return cov / (std_x * std_y)

    def compute_all_pairs(self) -> list[dict]:
        """Compute correlations for all configured pairs."""
        results = []
        for sym_a, sym_b in config.CORRELATION_PAIRS:
            results.append(self.compute_correlation(sym_a, sym_b))
        return results


# Global instance
correlation_tracker = CorrelationTracker()
