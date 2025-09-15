import logging, time
from typing import Dict, Any

logger = logging.getLogger(__name__)

class IcebergExecutor:
    """
    Iceberg Executor
    - Only shows a small portion of order at a time
    - Hides true size to avoid market impact
    """

    def __init__(self, order_manager, display_size: int = 10, delay: float = 0.1):
        self.order_manager = order_manager
        self.display_size = display_size
        self.delay = delay

    def execute(self, symbol: str, side: str, size: int, price: float) -> Dict[str, Any]:
        results = []
        remaining = size

        while remaining > 0:
            slice_size = min(self.display_size, remaining)
            try:
                res = self.order_manager.place_order(symbol, side, slice_size, price)
                results.append(res)
                remaining -= slice_size
                logger.info(f"[Iceberg] Display {slice_size}/{size} → {res['status']} | Remaining={remaining}")
                time.sleep(self.delay)
            except Exception as e:
                logger.error(f"[Iceberg] Execution failed: {e}")
                return {"status": "error", "reason": "Iceberg execution failure", "details": results}

        return {"status": "filled", "algo": "Iceberg", "details": results}
