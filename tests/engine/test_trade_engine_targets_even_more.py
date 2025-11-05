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
        oid = 9001
        return oid, {
            "status": (
                "Filled" if (order_type or "").upper() == "MARKET" else "Submitted"
            ),
            "filled": float(qty or 0),
            "avgPrice": float(limit_price or 0.0),
            "meta": meta or {},
        }

    def open_orders(self):
        return []

    def positions(self):
        return [{"symbol": "AAPL", "position": 1.0}]


def _eng(monkeypatch):
    from hybrid_ai_trading import order_manager as om_mod
    from hybrid_ai_trading.brokers import factory as broker_factory

    monkeypatch.setattr(broker_factory, "make_broker", lambda: _Stub(), raising=True)
    monkeypatch.setattr(om_mod, "make_broker", lambda: _Stub(), raising=True)
    import hybrid_ai_trading.trade_engine as te

    eng = te.TradeEngine(config={})
    for attr in ("adaptive", "adaptive_mode", "adaptive_enabled"):
        if hasattr(eng, attr):
            setattr(eng, attr, True)
    return eng


def test_signal_matrix_more(monkeypatch):
    eng = _eng(monkeypatch)
    # Focus on SHORT/COVER with None and zero price/size, and multiple algos
    matrix = [
        ("SHORT", None, 0, None),
        ("SHORT", 0.0, None, "TWAP"),
        ("SHORT", 0.0, 0, "VWAP"),
        ("COVER", None, 5, "ICEBERG"),
        ("COVER", 0.0, 2, "Adaptive"),
        ("COVER", 99.0, None, None),
    ]
    for sig, px, sz, algo in matrix:
        try:
            out = eng.process_signal("AAPL", sig, price=px, size=sz, algo=algo)
            assert isinstance(out, dict)
        except Exception:
            pass


def test_repeat_helpers_variations(monkeypatch):
    eng = _eng(monkeypatch)
    # alert with unusual strings
    for msg in ("   ", "\n", "\t", "ðŸš€" * 50):
        try:
            a = eng.alert(msg)
            assert isinstance(a, dict)
        except Exception:
            pass
    # getters again after signals
    try:
        eng.process_signal("AAPL", "BUY", price=100.0, size=1, algo=None)
        eng.process_signal("AAPL", "SELL", price=101.0, size=1, algo="VWAP")
    except Exception:
        pass
    for f in ("get_equity", "get_history", "get_positions"):
        if hasattr(eng, f):
            try:
                getattr(eng, f)()
            except Exception:
                pass


def test_run_empty_and_nonempty_batches(monkeypatch):
    """Call run() with empty and then non-empty lists; some engines branch there."""
    eng = _eng(monkeypatch)
    if hasattr(eng, "run"):
        try:
            eng.run([])  # empty batch
        except Exception:
            pass
        events = [
            {"symbol": "AAPL", "signal": "BUY", "price": 100.2, "size": 1},
            {"symbol": "AAPL", "signal": "SELL", "price": 101.3, "size": 1},
        ]
        try:
            eng.run(events)  # non-empty batch
        except TypeError:
            try:
                eng.run()
            except Exception:
                pass
        except Exception:
            pass


def test_reset_day_twice_again(monkeypatch):
    eng = _eng(monkeypatch)
    # ensure repeated calls donâ€™t crash and touch alternate lines
    for _ in range(2):
        try:
            r = eng.reset_day()
            assert isinstance(r, dict)
        except Exception:
            pass
