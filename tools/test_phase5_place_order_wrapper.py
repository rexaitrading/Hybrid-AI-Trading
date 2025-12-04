"""
Sanity-test for place_order_phase5 wrapper against Phase-5 decisions JSON.
"""

from hybrid_ai_trading.tools.phase5_gating_helpers import load_decisions_for_symbol
from hybrid_ai_trading.execution.execution_engine import place_order_phase5_with_logging as place_order_phase5


class FakeEngine:
    def __init__(self) -> None:
        self.calls = []

    def place_order(self, *args, **kwargs):
        # Record that underlying engine was actually called
        self.calls.append((args, kwargs))
        return {
            "status": "ok",
            "engine_called": True,
            "args": args,
            "kwargs": kwargs,
        }


def main() -> None:
    symbol = "NVDA"
    decisions = load_decisions_for_symbol(symbol)
    blocked = [d for d in decisions if not d.allow_flag]
    allowed = [d for d in decisions if d.allow_flag]

    print(f"{symbol}: {len(decisions)} decisions, {len(blocked)} blocked, {len(allowed)} allowed")

    if not blocked or not allowed:
        print("Not enough diversity in NVDA decisions to test both paths.")
        return

    eng = FakeEngine()

    # Representative rows
    blocked_dec = blocked[0]
    allowed_dec = allowed[0]

    print("\\nTesting BLOCKED path...")
    res_blocked = place_order_phase5(
        eng,
        symbol=symbol,
        entry_ts=blocked_dec.entry_ts,
        side="BUY",
        qty=1.0,
        price=None,
        regime="NVDA_BPLUS_REPLAY",
    )
    print("Blocked result:", res_blocked)
    print("Engine calls after blocked:", len(eng.calls))

    print("\\nTesting ALLOWED path...")
    res_allowed = place_order_phase5(
        eng,
        symbol=symbol,
        entry_ts=allowed_dec.entry_ts,
        side="BUY",
        qty=1.0,
        price=None,
        regime="NVDA_BPLUS_REPLAY",
    )
    print("Allowed result:", res_allowed)
    print("Engine calls after allowed:", len(eng.calls))


if __name__ == "__main__":
    main()

def test_phase5_place_order_wrapper() -> None:
    """
    Pytest wrapper that exercises main() once. This ensures the
    place_order_phase5 wrapper can load decisions for NVDA and
    run both the blocked and allowed paths without raising.
    """
    main()