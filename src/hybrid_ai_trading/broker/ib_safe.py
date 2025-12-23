from __future__ import annotations

import os
from typing import Any, Optional

from hybrid_ai_trading.execution.blockg_enforce import require_blockg_ready_for_live


def _is_live() -> bool:
    return str(os.environ.get("HAT_IS_PAPER", "")).strip() == "0"


def _infer_symbol(contract: Any) -> Optional[str]:
    # Best-effort: supports ib_insync Contract-like objects + stubs used in tests.
    for attr in ("symbol", "localSymbol"):
        try:
            v = getattr(contract, attr, None)
            if v:
                return str(v).upper()
        except Exception:
            pass
    return None


def ib_place_order_chokepoint(ib, *args):
    """
    Single chokepoint for raw IB placeOrder.

    Supported call styles:
      - ib_place_order_chokepoint(ib, contract, order)                   # order_id defaults to 0
      - ib_place_order_chokepoint(ib, order_id, contract, order)         # explicit order_id

    Institutional safety:
      - If live (HAT_IS_PAPER=0) and symbol is NVDA/SPY/QQQ, enforce Block-G readiness.
    """
    if len(args) == 2:
        contract, order = args
        order_id = 0
    elif len(args) == 3:
        order_id, contract, order = args
    else:
        raise TypeError(
            f"ib_place_order_chokepoint expected 2 or 3 args after ib, got {len(args)}"
        )

    if _is_live():
        sym = _infer_symbol(contract)
        if sym in ("NVDA", "SPY", "QQQ"):
            require_blockg_ready_for_live(sym)

    try:
        return ib.placeOrder(order_id, contract, order)
    except TypeError:
        # Some mocks / wrappers expose placeOrder(contract, order)
        return ib.placeOrder(contract, order)
