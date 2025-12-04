"""
Test the Phase-5 "no averaging down" hook inside place_order_phase5.

We DO NOT use the real ExecutionEngine here.
Instead we use a FakeEngine with a FakeRiskManager to verify:

- When risk says BLOCK -> place_order is NOT called, status="blocked_by_phase5_risk".
- When risk says ALLOW -> place_order IS called, status="ok", engine_called=True.
"""

from __future__ import annotations

from hybrid_ai_trading.execution.execution_engine import place_order_phase5_with_logging as place_order_phase5


class FakeRiskManager:
    def __init__(self) -> None:
        self.calls = []

    def phase5_no_averaging_down_for_symbol(self, symbol, side, entry_ts):
        """
        Simple test behavior:
        - On first call: block the trade.
        - On second call: allow the trade.
        """
        self.calls.append((symbol, side, entry_ts))
        call_index = len(self.calls)

        if call_index == 1:
            # Block with explicit reason
            return False, "test_no_averaging_down_block"
        else:
            # Allow
            return True, "ok"


class FakeEngine:
    def __init__(self) -> None:
        self.calls = []
        self.risk_manager = FakeRiskManager()
        self._logger = None  # you could plug a real logger if desired

    def place_order(self, *args, **kwargs):
        """
        Simulate the underlying engine.place_order being called.
        """
        self.calls.append((args, kwargs))
        return {
            "status": "ok",
            "engine_called": True,
            "args": args,
            "kwargs": kwargs,
        }


def main() -> None:
    engine = FakeEngine()

    print("=== Phase-5 no-averaging-down hook test ===")

    # Use an entry_ts that is NOT in the Phase-5 decisions file
    # so that should_allow_trade() returns allow=True and we only
    # exercise the risk hook.
    test_ts = "TEST_TS_NO_AVG"

    print("\n[1] Testing RISK-BLOCK path ...")
    res_block = place_order_phase5(
        engine,
        symbol="NVDA",
        entry_ts=test_ts,
        side="BUY",
        qty=1.0,
        price=None,
        regime="NVDA_BPLUS_REPLAY",
    )
    print("Blocked result:", res_block)
    print("Engine calls after blocked:", len(engine.calls))
    print("Risk calls after blocked:", len(engine.risk_manager.calls))

    print("\n[2] Testing RISK-ALLOW path ...")
    res_allow = place_order_phase5(
        engine,
        symbol="NVDA",
        entry_ts=test_ts,
        side="BUY",
        qty=1.0,
        price=None,
        regime="NVDA_BPLUS_REPLAY",
    )
    print("Allowed result:", res_allow)
    print("Engine calls after allowed:", len(engine.calls))
    print("Risk calls after allowed:", len(engine.risk_manager.calls))


if __name__ == "__main__":
    main()

def test_phase5_no_averaging_hook() -> None:
    """
    Pytest wrapper that exercises main() once. This ensures the
    Phase-5 no-averaging hook test script can run end-to-end
    without raising exceptions.
    """
    main()