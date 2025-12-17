from __future__ import annotations

from dataclasses import dataclass
from typing import List

from hybrid_ai_trading.blockg_contract import require_blockg_ready
from hybrid_ai_trading.runtime.run_context import RunContext, RunMode


@dataclass(frozen=True)
class BlockGRuntimeDecision:
    ok: bool
    reasons: List[str]


def enforce_blockg_if_live(ctx: RunContext, symbol: str) -> BlockGRuntimeDecision:
    """
    Single shared fail-closed gate:
      - PAPER/REPLAY: ok=True (never block artifact/sim)
      - LIVE: must pass require_blockg_ready(symbol) (contract truth)
    """
    if ctx.mode != RunMode.LIVE:
        return BlockGRuntimeDecision(ok=True, reasons=["NON_LIVE_MODE"])

    d = require_blockg_ready(symbol)
    if not d.ready:
        return BlockGRuntimeDecision(ok=False, reasons=[f"{d.reason}"])
    return BlockGRuntimeDecision(ok=True, reasons=["OK"])