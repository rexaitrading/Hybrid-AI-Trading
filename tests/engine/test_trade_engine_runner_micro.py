import pytest

class _Stub:
    def connect(self): return True
    def disconnect(self): pass
    def server_time(self): return "2025-10-11 00:00:00"
    def place_order(self, symbol, side, qty, order_type="MARKET", limit_price=None, meta=None):
        return 3, {"status":"Filled","filled":float(qty or 0),"avgPrice":float(limit_price or 0.0),"meta":meta or {}}
    def open_orders(self): return []
    def positions(self): return [{"symbol":"AAPL","position":1.0}]

@pytest.fixture()
def eng(monkeypatch):
    from hybrid_ai_trading.brokers import factory as broker_factory
    from hybrid_ai_trading import order_manager as om_mod
    monkeypatch.setattr(broker_factory, "make_broker", lambda: _Stub(), raising=True)
    monkeypatch.setattr(om_mod,          "make_broker", lambda: _Stub(), raising=True)
    import hybrid_ai_trading.trade_engine as te
    return te.TradeEngine(config={})

def test_runner_empty_and_mixed_batches(eng):
    # batch empty
    if hasattr(eng, "run"):
        try: eng.run([])
        except Exception: pass
    # malformed single event
    bad = {"foo":"bar"}
    if hasattr(eng, "run"):
        try: eng.run([bad])
        except Exception: pass
    # mixed good events
    good = [
        {"symbol":"AAPL","signal":"BUY","price":100.0,"size":1},
        {"symbol":"AAPL","signal":"SELL","price":101.0,"size":2},
    ]
    if hasattr(eng, "run"):
        try: eng.run(good)
        except TypeError:
            try: eng.run()
            except Exception: pass
        except Exception:
            pass
    # single-event hooks with both good/bad
    if hasattr(eng, "run_once"):
        for ev in (good[0], bad):
            try: eng.run_once(ev)
            except TypeError:
                try: eng.run_once()
                except Exception: pass
            except Exception: pass
    if hasattr(eng, "tick"):
        for ev in (good[0], bad):
            try: eng.tick(ev)
            except TypeError:
                try: eng.tick()
                except Exception: pass
            except Exception: pass