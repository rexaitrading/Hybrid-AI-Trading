from __future__ import annotations

from typing import Any, Dict

from hybrid_ai_trading.risk.risk_phase5_types import Phase5RiskDecision
from hybrid_ai_trading.execution.blockg_contract import ensure_symbol_blockg_ready as contract_ensure_symbol_blockg_ready
def place_order_with_phase5_guard(
    rm: Any,
    ib_client: Any,
    contract: Any,
    order: Any,
    trade_context: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Minimal IB wrapper for Phase-5 guard, used by tests.

    Tests provide a RiskManager-like stub with check_trade_phase5 returning
    Phase5RiskDecision(allowed=True, ...). We do NOT actually call IB here;
    we just return a dict for the tests to inspect.
    """
    if rm is None:
        raise RuntimeError("RiskManager is required for Phase-5 IB guard")

    # Block-G fail-closed for NVDA LIVE regimes
    sym = str(trade_context.get("symbol","")).upper()
    reg = str(trade_context.get("regime","")).upper()
    if sym == "NVDA" and ("LIVE" in reg):
        contract_ensure_symbol_blockg_ready("NVDA", allow_paper=False, is_paper=False, ctx=None)

    decision = rm.check_trade_phase5(trade_context)
    if not isinstance(decision, Phase5RiskDecision):
        raise TypeError("check_trade_phase5 must return Phase5RiskDecision")

    if not decision.allowed:
        return {
            "status": "blocked_by_phase5_risk",
            "reason": decision.reason,
            "decision": {
                "allowed": decision.allowed,
                "reason": decision.reason,
                "details": decision.details,
            },
        }

    # Happy path stub: IB order is assumed ok
    return {
        "status": "ok_stub_ib",
        "reason": decision.reason,
        "trade_context": trade_context,
    }