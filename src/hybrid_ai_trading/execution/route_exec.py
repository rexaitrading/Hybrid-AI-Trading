import os
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any
from hybrid_ai_trading.execution.broker_api import place_limit
def place_entry(symbol: str, side: str, qty: int, limit_price: float, risk_manager=None) -> Dict[str, Any]:
    """
    Risk-aware entry wrapper for the ExecRouter:
      - computes notional = qty * limit_price
      - optional risk_manager.approve_trade(symbol, side, qty, notional)
      - DRY_RUN=1 guard
      - routes via broker_api.place_limit on approval
    Returns dict with broker/status/resp fields (same shape as broker_api).
    """
    from hybrid_ai_trading.execution.broker_api import place_limit  # local import keeps deps light

    try:
        side_u = str(side).upper()
    except Exception:
        side_u = "BUY"

    qty_i = int(qty) if qty is not None else 0
    lp_f = float(limit_price) if limit_price is not None else 0.0
    if qty_i <= 0 or lp_f <= 0:
        return {"status": "skip", "reason": "bad_qty_or_price"}

    notional = float(qty_i) * lp_f

    # optional external risk gate
    if risk_manager is not None:
        try:
            gate = risk_manager.approve_trade(symbol, side_u, qty_i, notional)
            # normalize gate output: (ok,reason) | dict | bool
            if isinstance(gate, dict):
                ok, reason = bool(gate.get("approved")), str(gate.get("reason",""))
            elif isinstance(gate, (tuple, list)) and gate:
                ok, reason = bool(gate[0]), ("" if len(gate)<2 else str(gate[1]))
            else:
                ok, reason = bool(gate), ""
            if not ok:
                return {"status": "veto", "reason": reason, "symbol": symbol, "side": side_u, "qty": qty_i, "limit": lp_f}
        except Exception as e:
            return {"status": "error", "reason": f"risk_error:{e}", "symbol": symbol, "side": side_u, "qty": qty_i, "limit": lp_f}

    # DRY-RUN guard
    if os.environ.get("DRY_RUN", "0") == "1":
        return {"status": "dry_run", "symbol": symbol, "side": side_u, "qty": qty_i, "limit": lp_f, "notional": notional}

    # Route via ExecRouter (IBKR primary)
    return place_limit(symbol, side_u, qty_i, lp_f)