import logging, time
from typing import Dict, Any

logger = logging.getLogger(__name__)

class TWAPExecutor:
    """
    TWAP (Time-Weighted Average Price) Executor
    - Splits an order into equal slices across time intervals
    - Configurable slices & delay
    """

    def __init__(self, order_manager, slices: int = 10, delay: float = 0.1):
        self.order_manager = order_manager
        self.slices = slices
        self.delay = delay

    def execute(self, symbol: str, side: str, size: int, price: float) -> Dict[str, Any]:
        slice_size = max(1, size // self.slices)
        results = []

        for i in range(self.slices):
            try:
                res = self.order_manager.place_order(symbol, side, slice_size, price)
                results.append(res)
                logger.info(f"[TWAP] Slice {i+1}/{self.slices} | {side} {slice_size} {symbol} @ {price} → {res['status']}")
                time.sleep(self.delay)
            except Exception as e:
                logger.error(f"[TWAP] Execution failed at slice {i+1}: {e}")
                return {"status": "error", "reason": "TWAP execution failure", "details": results}

        return {"status": "filled", "algo": "TWAP", "details": results}
