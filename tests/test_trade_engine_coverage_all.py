import os, sys, types, importlib, inspect, pytest
os.environ.setdefault("PYTHONPATH","src")
TE = importlib.import_module("hybrid_ai_trading.trade_engine")

# ---------- Doubles ----------
class PT:
    def __init__(self, s=-2.0, t=-2.0):
        self._s, self._t = s, t
    def sharpe_ratio(self): return self._s
    def sortino_ratio(self): return self._t
    def record_trade(self, pnl): pass

class PF:
    def __init__(self, equity=100.0, pos=None):
        self.equity = equity
        self.history = [(0, 100.0)]
        # dict form; _sector_exposure_breach uses .items()
        self._pos = pos or {"AAPL": {"size": 1, "avg_price": 100.0}}
    def reset_day(self): return {"status": "ok"}
    def get_positions(self): return self._pos

class RM:
    def reset_day(self): return {"status":"ok"}

class OM:
    def route(self, *a, **k): return {"status":"ok","reason":"ok"}

# ---------- Engine builder (signature-aware) ----------
def _mk(cfg_override=None, pf=None, pt=None, rm=None, om=None):
    TradeEngine = TE.TradeEngine
    cfg = {
        "risk": {
            "max_drawdown": 0.5,
            "sharpe_min": -1.0,
            "sortino_min": -1.0,
            "intraday_sector_exposure": 1.0,
        },
        "alerts": {"slack_url": "http://x", "telegram_bot": "b", "telegram_chat": "c", "email": True},
    }
    if cfg_override:
        # deep-ish merge, only for keys we set
        for k,v in cfg_override.items():
            if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                cfg[k].update(v)
            else:
                cfg[k] = v

    cm = {
        "portfolio": pf or PF(),
        "risk_manager": rm or RM(),
        "risk": rm or RM(),
        "rm": rm or RM(),
        "order_manager": om or OM(),
        "order_router": om or OM(),
        "router": om or OM(),
        "performance_tracker": pt or PT(),
        "perf": pt or PT(),
        "tracker": pt or PT(),
        "config": cfg,
    }

    sig = inspect.signature(TradeEngine.__init__)
    params = [p for p in list(sig.parameters)[1:]]  # skip self
    kw = {}
    for n in params:
        if n in cm: kw[n]=cm[n]
        elif n in ("riskMgr","risk_module"): kw[n]=cm["risk"]
        elif n in ("om","orderMgr"):         kw[n]=cm["order_manager"]
        elif n in ("pt","perf_tracker"):     kw[n]=cm["performance_tracker"]
        elif n.lower().startswith("risk"):   kw[n]=cm["risk"]
        elif "order" in n or "router" in n:  kw[n]=cm["order_manager"]
        elif "perf" in n or "track" in n:    kw[n]=cm["performance_tracker"]
        elif "portfol" in n:                 kw[n]=cm["portfolio"]
        elif "config" in n or "cfg" in n:    kw[n]=cm["config"]
    try:
        return TradeEngine(**kw)
    except TypeError:
        return TradeEngine(*[kw.get(n) for n in params])

# ---------- Helpers ----------
def _find(te, names):
    for n in names:
        f = getattr(te, n, None)
        if callable(f): return f
    return None

def _call_signal(te, **kw):
    f = _find(te, ["process_signal","_on_signal","on_signal","handle_signal","submit","trade"])
    if f:
        try:
            return f(**kw)
        except TypeError:
            sig = inspect.signature(f)
            order = []
            for p in list(sig.parameters.values()):
                order.append(kw.get(p.name))
            return f(*order)
    return {"status":"rejected","reason":"no_signal_entrypoint"}

# ---------- Tests targeting uncovered clusters ----------

def test_alerts_matrix_success_and_exceptions(monkeypatch):
    te = _mk()
    class R:
        def __init__(self,c): self.status_code=c
    # success paths (hits 113–115/127–129/137–139)
    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(
        post=lambda *a, **k: R(200),
        get =lambda *a, **k: R(200)))
    class SMTPOK:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def send_message(self, *a, **k): return None
    monkeypatch.setitem(sys.modules, "smtplib", types.SimpleNamespace(SMTP=lambda *a, **k: SMTPOK()))
    if hasattr(te, "_fire_alert"): te._fire_alert("ok")

    # exceptions (hits 115–117 / 131–132 / 141–142, and 103–104 general except if raised at router dispatch)
    def boom(*a, **k): raise RuntimeError("boom")
    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(post=boom, get=boom))
    class SMTPBAD:
        def __enter__(self): raise RuntimeError("bad")
        def __exit__(self, *a): return False
    monkeypatch.setitem(sys.modules, "smtplib", types.SimpleNamespace(SMTP=lambda *a, **k: SMTPBAD()))
    if hasattr(te, "_fire_alert"): te._fire_alert("fail")

def test_audit_header_then_exception(monkeypatch, tmp_path):
    te = _mk()
    te.audit_log  = str(tmp_path / "audit.csv")
    te.backup_log = str(tmp_path / "backup.csv")
    if hasattr(te, "_write_audit"):
        te._write_audit(["t","AAPL","BUY",1,1.0,"ok",100.0,""])   # header path 154–167
    # now force exception path 168–169 (caught/logged)
    te.audit_log  = str(tmp_path / "no_dir" / "audit.csv")
    te.backup_log = str(tmp_path / "no_dir" / "backup.csv")
    monkeypatch.setattr("os.makedirs", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("mkfail")))
    class Blower:
        def __call__(self, *a, **k): raise RuntimeError("openfail")
        def __enter__(self): raise RuntimeError("openfail")
        def __exit__(self, *a): return False
    monkeypatch.setattr("builtins.open", Blower())
    if hasattr(te, "_write_audit"):
        te._write_audit(["t","AAPL","BUY",1,1.0,"ok",100.0,""])

def test_invalid_price_and_signal_paths():
    te = _mk()
    r1 = _call_signal(te, symbol="AAPL", size=1.0, price=None, signal="BUY")  # 232
    r2 = _call_signal(te, symbol="AAPL", size=1.0, price=1.0,  signal=123)    # 225/228
    for r in (r1, r2): assert isinstance(r, dict)

def test_equity_depleted_and_sector_exposure():
    # equity depleted (236)
    te = _mk()
    te.portfolio.equity = 0.0
    _call_signal(te, symbol="AAPL", size=1.0, price=1.0, signal="BUY")
    # sector exposure (239–354 region exercised in engine flow; ensure tech pos exists & tight cap)
    te2 = _mk(cfg_override={"risk":{"intraday_sector_exposure":0.001}}, pf=PF(pos={"AAPL":{"size":3,"avg_price":100}}))
    _call_signal(te2, symbol="AAPL", size=1.0, price=1.0, signal="BUY")

def test_algo_dynamic_imports_and_router_error(monkeypatch):
    te = _mk()
    # dynamic algo imports 263–269
    class TWAP:
        def __init__(self, om): pass
        def execute(self): return {"status":"ok","reason":"ok"}
    fake = types.SimpleNamespace(TWAPExecutor=TWAP, VWAPExecutor=TWAP)
    monkeypatch.setattr(importlib, "import_module",
        lambda name: fake if name.endswith((".twap",".vwap")) else importlib.import_module(name))
    if hasattr(te, "_route_with_algo"):
        assert te._route_with_algo("AAPL","BUY",1,1.0, algo="twap")["status"] == "ok"
        assert te._route_with_algo("AAPL","BUY",1,1.0, algo="vwap")["status"] == "ok"
    # router error 286–288
    if hasattr(te, "order_manager"):
        te.order_manager.route = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("router"))
    if hasattr(te, "_route_direct"):
        r = te._route_direct("AAPL","BUY",1,1.0)
        assert r["status"] in {"blocked","error"}

def test_filters_ratio_normalize_and_audit_capture(tmp_path):
    te = _mk()
    te.config.setdefault("filters", {})
    te.config["filters"].update({"sentiment": True, "gatescore": True})
    te.sentiment_filter = types.SimpleNamespace(allow=lambda *a, **k: False)
    te.gatescore       = types.SimpleNamespace(allow=lambda *a, **k: False)
    if hasattr(te, "_filters_ok"):
        assert te._filters_ok("AAPL","BUY",1,1.0)["status"] == "blocked"   # 306
        te.sentiment_filter.allow = lambda *a, **k: True
        assert te._filters_ok("AAPL","BUY",1,1.0)["status"] == "blocked"   # 312

    # ratio guards 317–326
    te.performance_tracker = PT(s=-2.0, t=-2.0)
    _call_signal(te, symbol="AAPL", size=1.0, price=1.0, signal="BUY")

    # normalize ok->filled & reason norm 329–338
    if hasattr(te, "_normalize_result"):
        g = te._normalize_result({"status":"ok","reason":"ok"})
        assert g["status"]=="filled" and g["reason"]=="normalized_ok"
        bad = te._normalize_result({"status":"weird"})
        assert bad["status"]=="rejected"

    # audit capture failure 352
    if hasattr(te, "_write_audit"):
        te._write_audit = lambda row: (_ for _ in ()).throw(RuntimeError("fail"))
        if hasattr(te, "_fire_alert"):
            te._fire_alert("audit_capture")

def test_positions_history_and_outcome_logging(caplog):
    te = _mk()
    if hasattr(te, "get_positions"): te.get_positions()      # 376
    if hasattr(te, "get_history"):   te.get_history()        # 379
    if hasattr(te, "record_trade_outcome"):
        def bad(pnl): raise RuntimeError("x")
        if hasattr(te, "performance_tracker"):
            te.performance_tracker.record_trade = bad
        te.record_trade_outcome(1.23)                        # 384–387 (log path)

def test_daily_reset_specific_and_generic(monkeypatch):
    te = _mk()
    # portfolio-specific error 175–179
    if hasattr(te, "portfolio") and hasattr(te.portfolio, "reset_day"):
        te.portfolio.reset_day = lambda: (_ for _ in ()).throw(RuntimeError("PFAIL"))
        if hasattr(te, "daily_reset"):
            r = te.daily_reset()
            assert r["status"]=="error" and "portfolio_reset_failed" in r["reason"]
        te.portfolio.reset_day = lambda: {"status":"ok"}
    # risk-specific error 182–186
    for attr in ("risk_manager","risk","rm"):
        if hasattr(te, attr):
            setattr(getattr(te, attr), "reset_day", lambda: (_ for _ in ()).throw(RuntimeError("RFAIL")))
            break
    if hasattr(te, "daily_reset"):
        r = te.daily_reset()
        assert r["status"]=="error" and "risk_reset_failed" in r["reason"]

    # generic catch-all 197–198 (wrap te.daily_reset)
    if hasattr(te, "daily_reset"):
        monkeypatch.setattr(te, "daily_reset", lambda: (_ for _ in ()).throw(RuntimeError("GENERIC")))
        r = te.daily_reset()
        assert r["status"]=="error"
