from __future__ import annotations

class DummyRiskMgr:
    """
    Minimal risk manager for replay/micro-trials.
    Approves trades up to an optional per-trade notional cap.
    """
    def __init__(self, max_notional: float | None = None):
        self.max_notional = max_notional

    def approve(self, symbol: str, side: str, qty: float, notional: float) -> dict:
        return self.approve_trade(symbol, side, qty, notional)

    def approve_trade(self, symbol: str, side: str, qty: float, notional: float) -> dict:
        cap = self.max_notional
        if cap is not None and notional is not None and notional > cap:
            return {"approved": False, "reason": f"cap_exceeded:{cap}"}
        return {"approved": True, "reason": "dummy_ok"}
