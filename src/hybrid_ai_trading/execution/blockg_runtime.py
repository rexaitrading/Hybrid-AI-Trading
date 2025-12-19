from __future__ import annotations

from dataclasses import dataclass
from typing import List

from hybrid_ai_trading.execution.blockg_contract_reader import is_symbol_ready
from hybrid_ai_trading.runtime.run_context import RunContext, RunMode


@dataclass(frozen=True)
class BlockGRuntimeDecision:
    ok: bool
    reasons: List[str]


def enforce_blockg_if_live(ctx: RunContext, symbol: str, *, is_live: bool | None = None) -> BlockGRuntimeDecision:
    """
    Single shared fail-closed gate:
      - PAPER/REPLAY: ok=True (never block artifact/sim)
      - LIVE: must pass require_blockg_ready(symbol) (contract truth)
    """
    if is_live is None:
        is_live = (ctx.mode == RunMode.LIVE)
    if not is_live:
        return BlockGRuntimeDecision(ok=True, reasons=["NON_LIVE_MODE"])
    d = is_symbol_ready(symbol)
    if not d.ready:
        return BlockGRuntimeDecision(ok=False, reasons=[f"{d.reason}"])
    return BlockGRuntimeDecision(ok=True, reasons=["OK"])
# --- Back-compat shim (tests monkeypatch this symbol) ---
def require_blockg_ready(symbol: str):
    """
    Back-compat for tests. Delegates to contract reader single truth.
    """
    from hybrid_ai_trading.execution.blockg_contract_reader import is_symbol_ready
    return is_symbol_ready(symbol)
# --- End shim ---
