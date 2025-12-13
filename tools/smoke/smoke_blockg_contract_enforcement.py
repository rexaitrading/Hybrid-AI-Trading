from __future__ import annotations

from hybrid_ai_trading.execution.blockg_contract import load_blockg_status, nvda_blockg_ready
from hybrid_ai_trading.execution.execution_engine_phase5_guard import place_order_phase5_with_guard


class DummyEngine:
    def __init__(self, is_paper: bool) -> None:
        self.is_paper = is_paper
        self.risk_manager = None

    def place_order(self, **kwargs):
        return {"status": "ok", "engine_called": True}


def main() -> int:
    s = load_blockg_status()
    print("[SMOKE] as_of_date=", s.as_of_date, "nvda_ready=", nvda_blockg_ready(s))

    for is_paper in (False, True):
        label = "paper" if is_paper else "live"
        try:
            out = place_order_phase5_with_guard(
                DummyEngine(is_paper),
                symbol="NVDA",
                side="BUY",
                qty=1,
                price=100.0,
                regime="NVDA_BPLUS_LIVE",
                day_id="TEST",
            )
            print("[SMOKE]", label, "ALLOW", out.get("status"))
        except Exception as e:
            print("[SMOKE]", label, "BLOCK", type(e).__name__, str(e)[:180])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())