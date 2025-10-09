# src/hybrid_ai_trading/execution/latency_monitor.py
"""
Latency Monitor (Hybrid AI Quant Pro v3.0 – OE Hedge-Fund Grade, AAA Coverage)
-------------------------------------------------------------------------------
Tracks latency, rolling avg, breach count, and halts trading after threshold breaches.
"""

import logging
import time
from collections import deque
from typing import Any, Callable, Dict

logger = logging.getLogger("hybrid_ai_trading.execution.latency_monitor")


class LatencyMonitor:
    def __init__(
        self, threshold_ms: float = 500, max_breaches: int = 5, window: int = 50
    ):
        self.threshold = max(1e-6, threshold_ms / 1000.0)
        self.max_breaches = max_breaches
        self.breach_count = 0
        self.halt = False
        self.samples = deque(maxlen=max(1, window))

    def reset(self) -> None:
        """Reset state for new trading session."""
        self.breach_count = 0
        self.halt = False
        self.samples.clear()
        logger.info("LatencyMonitor reset: breach_count=0, halt=False")

    def _avg_latency(self) -> float:
        """Compute rolling average latency."""
        return sum(self.samples) / len(self.samples) if self.samples else 0.0

    def get_stats(self) -> Dict[str, Any]:
        """Snapshot stats for monitoring/audit dashboards."""
        return {
            "avg_latency": self._avg_latency(),
            "breach_count": self.breach_count,
            "halt": self.halt,
            "samples": len(self.samples),
            "last_latency": self.samples[-1] if self.samples else None,
        }

    def measure(self, func: Callable, *args, **kwargs) -> Dict[str, Any]:
        """Measure latency of func, track stats, and enforce halts."""
        start = time.perf_counter()
        try:
            result = func(*args, **kwargs)
        except Exception as exc:
            elapsed = time.perf_counter() - start
            self.samples.append(elapsed)
            logger.error("LatencyMonitor caught exception: %s", exc)
            return {"status": "error", "latency": elapsed, "result": exc}

        elapsed = time.perf_counter() - start
        self.samples.append(elapsed)

        if elapsed > self.threshold:
            self.breach_count += 1
            logger.warning(
                "Latency breach %.6fs > %.6fs (count=%d)",
                elapsed,
                self.threshold,
                self.breach_count,
            )
            if self.breach_count >= self.max_breaches:
                self.halt = True
                logger.critical(
                    "HALTING trading: max breaches reached (%d)", self.breach_count
                )
                return {"status": "halt", "latency": elapsed, "result": result}
            return {"status": "warning", "latency": elapsed, "result": result}

        return {"status": "ok", "latency": elapsed, "result": result}
