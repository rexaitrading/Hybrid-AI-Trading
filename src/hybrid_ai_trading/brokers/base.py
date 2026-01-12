from __future__ import annotations

from hybrid_ai_trading.runtime.run_context import RunContext
from hybrid_ai_trading.execution.blockg_contract import ensure_symbol_blockg_ready

from typing import Any, Dict, List, Optional, Protocol, Tuple

def _blockg_guard_live(symbol: str, ctx: RunContext | None = None) -> None:
    # Fail-closed for live NVDA/SPY/QQQ at the broker interface layer.
    sym = str(symbol).upper().strip()
    if sym not in ("NVDA","SPY","QQQ"):
        return

    # Determine LIVE intent from ctx.mode (authoritative) or ctx.is_paper.
    mode = str(getattr(ctx, "mode", "") or "").lower() if ctx is not None else ""
    ctx_is_paper = getattr(ctx, "is_paper", None) if ctx is not None else None
    env_live = (str(__import__("os").environ.get("HAT_IS_PAPER","")).strip() == "0") if (ctx is None) else False
    live = (mode == "live") or (ctx_is_paper is False) or ((ctx is None) and env_live)

    if live:
        # Contract owner (ctx-aware). Single source of truth.
        ensure_symbol_blockg_ready(sym, allow_paper=True, is_paper=False, ctx=ctx)

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
        ctx: RunContext | None = None,
    ) -> Tuple[int, Dict[str, Any]]: ...
    def open_orders(self) -> List[Dict[str, Any]]: ...
    def positions(self) -> List[Dict[str, Any]]: ...
