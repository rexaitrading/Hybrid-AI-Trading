from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import hybrid_ai_trading.execution.blockg_runtime as br
from hybrid_ai_trading.runtime.run_context import RunContext, RunMode


@dataclass(frozen=True)
class BlockGEnforcementResult:
    ok: bool
    reason: str


def enforce_blockg_lastmile(
    *,
    ctx: Optional[RunContext],
    symbol: str,
    intent_is_live: Optional[bool] = None,
) -> BlockGEnforcementResult:
    """
    Last-mile fail-closed Block-G enforcement.

    - If not LIVE: ok
    - If LIVE: must pass br.require_blockg_ready(symbol)
    """
    sym = str(symbol).upper()

    # Determine live intent
    if intent_is_live is None:
        if ctx is None:
            is_live = False
        else:
            is_live = (ctx.mode == RunMode.LIVE)
    else:
        is_live = bool(intent_is_live)

    if not is_live:
        return BlockGEnforcementResult(ok=True, reason="NON_LIVE")

    try:
        d = br.require_blockg_ready(sym)
        if not bool(getattr(d, "ready", False)):
            r = str(getattr(d, "reason", "BLOCKG_NOT_READY"))
            return BlockGEnforcementResult(ok=False, reason=r)
        return BlockGEnforcementResult(ok=True, reason="OK")
    except Exception as e:
        return BlockGEnforcementResult(ok=False, reason=f"BLOCKG_EXCEPTION:{type(e).__name__}")