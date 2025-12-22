from __future__ import annotations

def _blockg_guard_live(symbol: str, ctx: RunContext | None = None) -> None:
    # Fail-closed for live NVDA/SPY/QQQ at the broker interface layer.
    try:
        is_paper = True
        if ctx is not None:
            is_paper = bool(getattr(ctx, "is_paper", True))
        if (not is_paper) and str(symbol).upper() in ("NVDA","SPY","QQQ"):
            require_blockg_ready_for_live(str(symbol).upper())
    except Exception:
        # fail-safe: if we cannot determine mode, assume paper (do not send live)
        require_blockg_ready_for_live(str(symbol).upper())

from hybrid_ai_trading.runtime.run_context import RunContext
from hybrid_ai_trading.execution.blockg_enforce import require_blockg_ready_for_live

from typing import Any, Dict, List, Optional, Protocol, Tuple


class Broker(Protocol):
    def connect(self) -> bool: ...
    def disconnect(self) -> None: ...
    def server_time(self) -> Optional[str]: ...
    def place_order(
        self,
        symbol: str,
        side: str,
        qty: float,
        order_type: str = "MARKET",
        limit_price: Optional[float] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Tuple[int, Dict[str, Any]]: ...
    def open_orders(self) -> List[Dict[str, Any]]: ...
    def positions(self) -> List[Dict[str, Any]]: ...
