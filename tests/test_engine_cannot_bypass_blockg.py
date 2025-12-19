import pytest

import hybrid_ai_trading.execution.execution_engine_phase5_guard as g


class DummyEngine:
    # no run_context on purpose
    pass


def test_guard_has_entrypoint():
    # At least one canonical entrypoint must exist
    assert hasattr(g, "place_order_phase5_with_guard") or hasattr(g, "place_order_phase5")


def test_no_runcontext_fails_closed():
    eng = DummyEngine()

    # Use whichever entrypoint exists in this build
    fn = getattr(g, "place_order_phase5_with_guard", None) or getattr(g, "place_order_phase5", None)
    assert fn is not None

    trade = {"symbol": "NVDA", "side": "BUY", "qty": 1.0, "price": 100.0}

    with pytest.raises(Exception):
        fn(eng, trade)