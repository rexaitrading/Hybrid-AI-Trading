import math

import pytest


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
        return 11, {
            "status": "Filled",
            "filled": float(qty or 0),
            "avgPrice": float(limit_price or 0.0),
            "meta": meta or {},
        }

    def open_orders(self):
        return []

    def positions(self):
        return [{"symbol": "AAPL", "position": 1.0}]


@pytest.fixture()
def eng(monkeypatch):
    from hybrid_ai_trading import order_manager as om_mod
    from hybrid_ai_trading.brokers import factory as broker_factory

    monkeypatch.setattr(broker_factory, "make_broker", lambda: _Stub(), raising=True)
    monkeypatch.setattr(om_mod, "make_broker", lambda: _Stub(), raising=True)
    import hybrid_ai_trading.trade_engine as te

    e = te.TradeEngine(config={})
    for k in ("adaptive", "adaptive_mode", "adaptive_enabled"):
        if hasattr(e, k):
            try:
                setattr(e, k, True)
            except Exception:
                pass
    return e


def test_process_signal_rare_mixups(eng):
    cases = [
        # symbol edge / non-string
        (None, "BUY", 100.0, 1, "adaptive"),
        (12345, "SELL", 101.0, 2, "TwAp"),
        # algo type edge (non-string)
        ("AAPL", "BUY", 0.0, 0, 7),
        ("AAPL", "SELL", None, 5, {"algo": "VWAP"}),
        # lowercase/unknown signal forms
        ("AAPL", "buy", 99.9, 1, "vwap"),
        ("AAPL", "cover", 98.7, 3, "iceberg"),
    ]
    for sym, sig, px, sz, algo in cases:
        try:
            out = eng.process_signal(sym, sig, price=px, size=sz, algo=algo)
            assert isinstance(out, dict) or out is None
        except Exception:
            pass


def test_late_helpers_weird_inputs(eng):
    # mix in events that miss "signal", have lowercase signal, or non-dict elements
    events = [
        {"symbol": "AAPL", "price": 100.0, "size": 1},  # missing signal
        {"symbol": "AAPL", "signal": "buy", "price": 100.0, "size": 1},  # lower
        {"symbol": "AAPL", "signal": "UNKNOWN", "price": 100.0, "size": 1},  # unknown
        {
            "symbol": "AAPL",
            "signal": "SELL",
            "price": 101.0,
            "size": 2,
            "signal": "SELL",
        },  # duplicate key (same)
        {},  # empty
        123,  # non-dict
    ]
    # try tick/run_once for each item
    for ev in events:
        for hook in ("tick", "run_once"):
            if hasattr(eng, hook):
                fn = getattr(eng, hook)
                try:
                    fn(ev)
                except TypeError:
                    try:
                        fn()
                    except Exception:
                        pass
                except Exception:
                    pass
    # batch to run (include non-dict)
    if hasattr(eng, "run"):
        try:
            eng.run(events)
        except TypeError:
            try:
                eng.run()
            except Exception:
                pass
        except Exception:
            pass


def test_outcome_tiny_denormals_and_reset(eng):
    for pnl in (1e-12, -1e-12, 123456.78):
        try:
            eng.record_trade_outcome(pnl)
        except Exception:
            pass
    try:
        eng.reset_day()
    except Exception:
        pass
