"""
TWAP Executor (Hybrid AI Quant Pro v2.3 Ã¢â‚¬â€œ Hedge Fund Grade, AAA Coverage)
-------------------------------------------------------------------------
Responsibilities:
- Split large order into equal slices over time
- Submit each slice via OrderManager
- Normalize per-slice results with consistent fields
- Structured audit trail for testing & analytics
- Edge cases: zero/negative size, slice normalization, exception handling
"""

import logging
import time
from typing import Any, Dict, List

logger = logging.getLogger("hybrid_ai_trading.algos.twap_executor")


class TWAPExecutor:
    """
    TWAP (Time-Weighted Average Price) Executor.
    Splits an order into equal slices across fixed time intervals.
    """

    def __init__(
        self, order_manager: Any, slices: int = 10, delay: float = 0.1
    ) -> None:
        self.order_manager = order_manager
        # normalize: always at least 1 slice
        self.slices = max(1, int(slices))
        self.delay = float(delay)

    def execute(
        self, symbol: str, side: str, size: int, price: float
    ) -> Dict[str, Any]:
        """
        Execute a TWAP order.

        Args:
            symbol: instrument ticker
            side: "BUY" or "SELL"
            size: total order size
            price: reference price for slices

        Returns:
            dict: status, algo, and normalized slice-level details
        """
        if size <= 0 or price <= 0:
            logger.warning("[TWAP] Invalid parameters: size=%s price=%s", size, price)
            return {
                "status": "error",
                "reason": "invalid parameters",
                "algo": "TWAP",
                "details": [],
            }

        slice_size = max(1, size // self.slices)
        results: List[Dict[str, Any]] = []

        for i in range(self.slices):
            try:
                raw = self.order_manager.place_order(symbol, side, slice_size, price)

                status = raw.get("status", "unknown")
                if status == "ok":  # normalize common variant
                    status = "filled"

                normalized = {
                    "slice": i + 1,
                    "size": slice_size,
                    "status": status,
                    "price": raw.get("fill_price", price),
                    "broker": raw.get("broker", "simulator"),
                    "details": raw,  # full raw response for audit
                }
                results.append(normalized)

                logger.info(
                    "[TWAP] Slice %d/%d | %s %d %s @ %.2f Ã¢â€ â€™ %s",
                    i + 1,
                    self.slices,
                    side,
                    slice_size,
                    symbol,
                    price,
                    normalized["status"],
                )

                if self.delay > 0:
                    time.sleep(self.delay)

            except Exception as e:
                logger.error("[TWAP] Execution failed at slice %d: %s", i + 1, e)
                return {
                    "status": "error",
                    "reason": f"TWAP execution failure at slice {i+1}",
                    "algo": "TWAP",
                    "details": results,
                }

        return {"status": "filled", "algo": "TWAP", "details": results}
