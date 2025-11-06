"""
Iceberg Executor (Hybrid AI Quant Pro v2.0 Ã¢â‚¬â€œ Hedge Fund Level)
--------------------------------------------------------------
Responsibilities:
- Hide true order size by slicing into visible portions
- Submit display slices via OrderManager
- Normalize per-slice results with consistent fields
- Structured logging for audit
- Hedge-fund grade error handling
"""

import logging
import time
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class IcebergExecutor:
    """
    Iceberg Executor.
    Splits large orders into smaller "display" slices to reduce market impact.
    """

    def __init__(
        self,
        order_manager,
        display_size: int = 10,
        delay: float = 0.1,
    ) -> None:
        self.order_manager = order_manager
        # normalize: display size must be >= 1
        self.display_size = max(1, int(display_size))
        self.delay = float(delay)

    def execute(
        self,
        symbol: str,
        side: str,
        size: int,
        price: float,
    ) -> Dict[str, Any]:
        """
        Execute iceberg order by slicing into display orders.

        Args:
            symbol: Trading symbol (e.g. "AAPL")
            side: "BUY" or "SELL"
            size: Total size of the iceberg order
            price: Limit price

        Returns:
            dict with keys:
                - status: "filled" or "error"
                - algo: "Iceberg"
                - details: list of per-slice normalized results
        """
        results: List[Dict[str, Any]] = []

        if size <= 0:
            logger.warning(
                "[Iceberg] Zero/negative size for %s Ã¢â€ â€™ no execution", symbol
            )
            return {"status": "filled", "algo": "Iceberg", "details": results}

        remaining = size
        while remaining > 0:
            slice_size = min(self.display_size, remaining)
            try:
                raw = self.order_manager.place_order(symbol, side, slice_size, price)

                normalized = {
                    "slice": len(results) + 1,
                    "size": slice_size,
                    "status": raw.get("status", "unknown"),
                    "price": raw.get("fill_price", price),
                    "broker": raw.get("broker", "simulator"),
                    "details": raw,
                }
                results.append(normalized)
                remaining -= slice_size

                logger.info(
                    "[Iceberg] Slice %d | %s %d %s @ %.2f Ã¢â€ â€™ %s | Remaining=%d",
                    len(results),
                    side,
                    slice_size,
                    symbol,
                    price,
                    normalized["status"],
                    remaining,
                )

                if self.delay > 0:
                    time.sleep(self.delay)

            except Exception as e:
                logger.error("[Iceberg] Execution failed: %s", e)
                return {
                    "status": "error",
                    "reason": f"Iceberg execution failure at slice {len(results)+1}",
                    "algo": "Iceberg",
                    "details": results,
                }

        return {"status": "filled", "algo": "Iceberg", "details": results}
