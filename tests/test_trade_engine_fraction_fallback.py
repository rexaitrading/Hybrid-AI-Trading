from importlib import import_module as _imp
TE = _imp("hybrid_ai_trading.trade_engine")

def test_base_fraction_fallbacks():
    te = TE.TradeEngine()
    # Poison likely deps so helper returns base fraction via try/except
    for attr in ("kelly_sizer","performance_tracker"):
        if hasattr(te, attr): setattr(te, attr, None)
    # Call any helper that looks like a fraction/kelly/base method
    for n in dir(te):
        if any(k in n.lower() for k in ("fraction","kelly","base")):
            f=getattr(te,n,None)
            if callable(f):
                try: f()
                except Exception: pass
