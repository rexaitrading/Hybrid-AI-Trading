import inspect

import pytest


# function-scoped fixture so monkeypatch scope matches
@pytest.fixture()
def stubbed(monkeypatch):
    # wire a safe stub broker into engine
    class _Stub:
        def connect(self):
            return True

        def disconnect(self):
            pass

        def server_time(self):
            return "2025-10-11 00:00:00"

        def place_order(
            self, symbol, side, qty, order_type="MARKET", limit_price=None, meta=None
        ):
            return 1, {
                "status": "Filled",
                "filled": float(qty or 0),
                "avgPrice": float(limit_price or 0.0),
                "meta": meta or {},
            }

        def open_orders(self):
            return []

        def positions(self):
            return [{"symbol": "AAPL", "position": 1.0}]

    from hybrid_ai_trading import order_manager as om_mod
    from hybrid_ai_trading.brokers import factory as broker_factory

    monkeypatch.setattr(broker_factory, "make_broker", lambda: _Stub(), raising=True)
    monkeypatch.setattr(om_mod, "make_broker", lambda: _Stub(), raising=True)

    import hybrid_ai_trading.trade_engine as te

    eng = te.TradeEngine(config={})
    return eng


def test_print_hotspots(stubbed, capsys):
    eng = stubbed

    # define the suspected hotspots by name; adapt if your engine uses different names
    candidates = [
        "process_signal",
        "record_trade_outcome",
        "reset_day",
        "get_equity",
        "get_history",
        "get_positions",
        "alert",
        "run_once",
        "tick",
        "run",
    ]

    out = []
    out.append("=== trade_engine hotspots ===")
    for name in candidates:
        has = hasattr(eng, name)
        sig = ""
        if has:
            try:
                sig = str(inspect.signature(getattr(eng, name)))
            except Exception:
                sig = "()"
        out.append(f"{name:20} present={has}  sig={sig}")

    print("\n".join(out))
    captured = capsys.readouterr().out
    # keep the test always passing; just require our header
    assert "=== trade_engine hotspots ===" in captured
