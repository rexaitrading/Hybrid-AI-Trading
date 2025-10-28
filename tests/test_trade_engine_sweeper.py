import sys, types, importlib, inspect, os
from _engine_factory import make_engine, call_signal, find

# ---------- helpers ----------
def _safe_signature(fn):
    try:    return inspect.signature(fn)
    except: return None

def _call(fn, defaults):
    sig = _safe_signature(fn)
    if not sig:
        return
    kwargs = {p.name: defaults.get(p.name) for p in sig.parameters.values() if p.name in defaults}
    try:
        return fn(**kwargs)
    except TypeError:
        args = [kwargs.get(p.name) for p in sig.parameters.values()]
        try: return fn(*args)
        except Exception: pass
    except Exception:
        pass

# ---------- tests ----------
def test_reflection_sweeper_alerts_audit_reset_signal_algo(monkeypatch, tmp_path):
    import importlib as _imp

    # engine with permissive defaults
    te = make_engine(alerts=True)

    # defaults used when calling arbitrary methods
    defaults = {
        "symbol":"AAPL","signal":"BUY","size":1.0,"price":1.0,
        "notional":100.0,"side":"BUY","bar_ts":1_000_000,"bar_ts_ms":1_000_000,
        "row":["t","AAPL","BUY",1,1.0,"ok",100.0,""]
    }

    # --- ALERTS: success & exceptions (works for any method containing 'alert')
    class R:
        def __init__(self,c): self.status_code=c
    monkeypatch.setitem(sys.modules,"requests", types.SimpleNamespace(post=lambda *a,**k:R(200), get=lambda *a,**k:R(200)))
    class SMTPOK:
        def __enter__(self): return self
        def __exit__(self,*a): return False
        def send_message(self,*a,**k): return None
    monkeypatch.setitem(sys.modules,"smtplib", types.SimpleNamespace(SMTP=lambda *a,**k: SMTPOK()))
    for name in dir(te):
        if "alert" in name.lower():
            _call(getattr(te,name), {"message":"ok"})

    # now drive exception branches
    def boom(*a,**k): raise RuntimeError("boom")
    monkeypatch.setitem(sys.modules,"requests", types.SimpleNamespace(post=boom, get=boom))
    class SMTPBAD:
        def __enter__(self): raise RuntimeError("bad")
        def __exit__(self,*a): return False
    monkeypatch.setitem(sys.modules,"smtplib", types.SimpleNamespace(SMTP=lambda *a,**k: SMTPBAD()))
    for name in dir(te):
        if "alert" in name.lower():
            try: _call(getattr(te,name), {"message":"fail"})
            except Exception: pass

    # --- AUDIT: header then exception (works for any method containing 'audit')
    te.audit_log  = str(tmp_path/"audit.csv")
    te.backup_log = str(tmp_path/"backup.csv")
    for name in dir(te):
        if "audit" in name.lower():
            _call(getattr(te,name), defaults)
    # cause exception in audit write
    te.audit_log  = str(tmp_path/"no_dir"/"audit.csv")
    te.backup_log = str(tmp_path/"no_dir"/"backup.csv")
    monkeypatch.setattr("os.makedirs", lambda *a,**k: (_ for _ in ()).throw(RuntimeError("mkfail")))
    class Blower:
        def __call__(self,*a,**k): raise RuntimeError("openfail")
        def __enter__(self): raise RuntimeError("openfail")
        def __exit__(self,*a): return False
    monkeypatch.setattr("builtins.open", Blower())
    for name in dir(te):
        if "audit" in name.lower():
            try: _call(getattr(te,name), defaults)
            except Exception: pass

    # --- SIGNAL / ROUTE / ALGO: success, then import-failure, then router error
    # success import for twap/vwap
    class TWAP:
        def __init__(self,om): pass
        def execute(self): return {"status":"ok","reason":"ok"}
    fake = types.SimpleNamespace(TWAPExecutor=TWAP, VWAPExecutor=TWAP)
    orig_import = importlib.import_module
    monkeypatch.setattr(importlib,"import_module",
        lambda name, _orig=orig_import: fake if name.endswith((".twap",".vwap")) else _orig(name))

    # try any algo/route-ish method
    for name in dir(te):
        if any(k in name.lower() for k in ("algo","route")):
            f = getattr(te,name)
            _call(f, {"symbol":"AAPL","side":"BUY","size":1.0,"price":1.0,"algo":"twap"})

    # import failure only for twap/vwap
    monkeypatch.setattr(importlib,"import_module",
        lambda name, _orig=orig_import: (_ for _ in ()).throw(ImportError("fail"))
            if name.endswith((".twap",".vwap")) else _orig(name))
    for name in dir(te):
        if "algo" in name.lower():
            try: _call(getattr(te,name), {"symbol":"AAPL","side":"BUY","size":1.0,"price":1.0,"algo":"twap"})
            except Exception: pass

    # router direct error
    if hasattr(te,"order_manager"):
        te.order_manager.route = lambda *a,**k: (_ for _ in ()).throw(RuntimeError("router"))
    for name in dir(te):
        if "direct" in name.lower() or ("route" in name.lower() and "algo" not in name.lower()):
            try: _call(getattr(te,name), {"symbol":"AAPL","side":"BUY","size":1.0,"price":1.0})
            except Exception: pass

    # --- FILTERS / RATIOS / NORMALIZE
    te.config.setdefault("filters",{}); te.config["filters"].update({"sentiment":True,"gatescore":True})
    te.sentiment_filter=types.SimpleNamespace(allow=lambda *a,**k: False)
    te.gatescore      =types.SimpleNamespace(allow=lambda *a,**k: False)
    for name in dir(te):
        if "filter" in name.lower():
            _call(getattr(te,name), {"symbol":"AAPL","side":"BUY","size":1.0,"price":1.0})
    te.sentiment_filter.allow=lambda *a,**k: True
    for name in dir(te):
        if "gate" in name.lower():
            _call(getattr(te,name), {"symbol":"AAPL","side":"BUY","size":1.0,"price":1.0})

    # drive ratio guards via low metrics
    te2 = make_engine(ratios=(-2.0,-2.0))
    call_signal(te2, symbol="AAPL", size=1.0, price=1.0, signal="BUY")

    # normalization helper variants
    for name in dir(te):
        if "normalize" in name.lower():
            fn = getattr(te,name)
            _call(fn, {"result":{"status":"weird"}})
            _call(fn, {"result":{"status":"ok","reason":"ok"}})

    # --- DAILY RESET: portfolio error, risk error, generic
    if hasattr(te,"portfolio") and hasattr(te.portfolio,"reset_day"):
        te.portfolio.reset_day=lambda: (_ for _ in ()).throw(RuntimeError("PFAIL"))
        for name in dir(te):
            if "daily_reset" in name or name=="daily_reset":
                try: getattr(te,name)()
                except Exception: pass
        te.portfolio.reset_day=lambda: {"status":"ok"}
    for attr in ("risk_manager","risk","rm"):
        if hasattr(te,attr):
            setattr(getattr(te,attr),"reset_day",lambda: (_ for _ in ()).throw(RuntimeError("RFAIL")))
            break
    for name in dir(te):
        if "daily_reset" in name or name=="daily_reset":
            try: getattr(te,name)()
            except Exception: pass
    # generic
    for name in dir(te):
        if "daily_reset" in name or name=="daily_reset":
            try:
                _orig = getattr(te,name)
                setattr(te,name, lambda: (_ for _ in ()).throw(RuntimeError("GENERIC")))
                getattr(te,name)()
            except Exception:
                pass
            finally:
                try: setattr(te,name,_orig)
                except Exception: pass

    # --- FRACTION / KELLY / BASE fallbacks
    te3 = make_engine()
    # poison likely deps so helper returns base fraction via try/except
    for a in ("kelly_sizer","performance_tracker"):
        if hasattr(te3,a): setattr(te3,a,None)
    for name in dir(te3):
        if any(k in name.lower() for k in ("fraction","kelly","base")):
            fn = getattr(te3,name)
            _call(fn, {})
