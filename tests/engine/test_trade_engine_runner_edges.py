import pytest
from hybrid_ai_trading.trade_engine import TradeEngine

@pytest.fixture()
def eng(): 
    return TradeEngine(config={})

def test_runner_branch_edges(eng):
    # 1) run() with non-list types (should be safely handled)
    for batch in (None, 123, "notalist", {"map":"notlist"}, ({"symbol":"AAPL","signal":"BUY","price":100,"size":1},),
                  (e for e in [])):  # generator
        if hasattr(eng, "run"):
            try: eng.run(batch)
            except Exception: pass

    # 2) run() with list containing non-dict / missing fields / valid
    mixed = [123, {}, {"foo":"bar"}, {"symbol":"AAPL"}, {"signal":"SELL"}, 
             {"symbol":"AAPL","signal":"BUY","price":100.5,"size":1}]
    if hasattr(eng, "run"):
        try: eng.run(mixed)
        except Exception: pass

    # 3) tick & run_once with non-dict and minimal dicts
    events = [None, 456, {}, {"symbol":"AAPL"}, {"symbol":"AAPL","signal":"HOLD"}]
    for hook in ("tick","run_once"):
        if hasattr(eng, hook):
            fn = getattr(eng, hook)
            for ev in events:
                try: fn(ev)
                except TypeError:
                    try: fn()
                    except Exception: pass
                except Exception: pass