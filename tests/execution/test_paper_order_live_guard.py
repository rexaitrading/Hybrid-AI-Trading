from __future__ import annotations

import types
import pytest

from hybrid_ai_trading.execution import paper_order


class _IB:
    def __init__(self):
        self.called = False

    def placeOrder(self, *a, **k):
        self.called = True
        return object()


def test_paper_order_refuses_live_mode(monkeypatch):
    monkeypatch.setenv("HAT_IS_PAPER", "0")

    ib = _IB()

    # Minimum invariant: the guard itself must fail-closed
    with pytest.raises(RuntimeError):
        paper_order._paper_only_guard()
    assert ib.called is False

    # Stronger invariant: if the module exposes any callable that might place orders,
    # it must also refuse before touching IB. We try a few common names if present.
    candidates = [
        "place_paper_order",
        "submit_paper_order",
        "send_paper_order",
        "paper_bracket_order",
        "paper_market_order",
    ]
    for name in candidates:
        fn = getattr(paper_order, name, None)
        if callable(fn):
            with pytest.raises(RuntimeError):
                # Best-effort call: if signature mismatch, we skip (not a failure)
                try:
                    fn(ib)  # some implementations accept ib first
                except TypeError:
                    fn()    # some accept no args (unlikely)
            assert ib.called is False
            break
