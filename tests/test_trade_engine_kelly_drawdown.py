from importlib import import_module as _imp
import inspect

TE = _imp("hybrid_ai_trading.trade_engine")

def _mk(hist):
    class PF2:
        def __init__(self):
            self.equity = 100.0
            self.history = hist
            self._pos = {"AAPL": {"size": 1, "avg_price": 100.0}}
        def reset_day(self): return {"status": "ok"}
        def get_positions(self): return self._pos

    # Minimal doubles
    OM = type("OM",(object,),{"route":lambda *a,**k: {"status":"ok","reason":"ok"}})
    PT = type("PT",(object,),{"sharpe_ratio":lambda s:0.0,"sortino_ratio":lambda s:0.0})
    cfg = {"risk":{"max_drawdown":0.5}}

    # Signature-aware ctor:
    TradeEngine = TE.TradeEngine
    sig = inspect.signature(TradeEngine.__init__)
    params = [p for p in list(sig.parameters)[1:]]  # skip self

    pool = {
        "portfolio": PF2(),
        "risk_manager": object(),
        "risk": object(),
        "rm": object(),
        "order_manager": OM(),
        "order_router": OM(),
        "router": OM(),
        "performance_tracker": PT(),
        "perf": PT(),
        "tracker": PT(),
        "config": cfg,
    }

    kwargs = {}
    for n in params:
        if n in pool: kwargs[n] = pool[n]
        elif n in ("riskMgr","risk_module"): kwargs[n] = pool["risk"]
        elif n in ("om","orderMgr"):         kwargs[n] = pool["order_manager"]
        elif n in ("pt","perf_tracker"):     kwargs[n] = pool["performance_tracker"]
        elif n.lower().startswith("risk"):   kwargs[n] = pool["risk"]
        elif "order" in n or "router" in n:  kwargs[n] = pool["order_manager"]
        elif "perf" in n or "track" in n:    kwargs[n] = pool["performance_tracker"]
        elif "portfol" in n:                 kwargs[n] = pool["portfolio"]
        elif "config" in n or "cfg" in n:    kwargs[n] = pool["config"]

    try:
        return TradeEngine(**kwargs)
    except TypeError:
        return TradeEngine(*[kwargs.get(n) for n in params])

def _find_signal(te):
    for n in ("process_signal","_on_signal","on_signal","handle_signal","submit","trade"):
        f = getattr(te, n, None)
        if callable(f): return f
    return None

def test_kelly_normal_and_drawdown_except():
    te1 = _mk(hist=[(0,100.0)])     # history present -> normal drawdown path
    f = _find_signal(te1)
    if f: f(symbol="AAPL", size=None, price=1.0, signal="BUY")

    te2 = _mk(hist=None)            # history None -> drawdown try/except branch
    f2 = _find_signal(te2)
    if f2: f2(symbol="AAPL", size=None, price=1.0, signal="BUY")
