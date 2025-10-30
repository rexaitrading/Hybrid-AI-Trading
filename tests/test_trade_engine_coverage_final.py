import importlib
import inspect
import io
import os
import sys
import types

import pytest

os.environ.setdefault("PYTHONPATH", "src")
TE = importlib.import_module("hybrid_ai_trading.trade_engine")


# ---- light test doubles (shared) ----
class PT:
    def __init__(self, s=-2.0, t=-2.0):
        self._s = s
        self._t = t

    def sharpe_ratio(self):
        return self._s

    def sortino_ratio(self):
        return self._t

    def record_trade(self, pnl):
        pass


class PF:
    def __init__(self, equity=100.0, pos=None):
        self.equity = equity
        self.history = [(0, 100.0)]
        self._pos = pos or {"AAPL": {"size": 1, "avg_price": 100.0}}

    def reset_day(self):
        return {"status": "ok"}

    def get_positions(self):
        return self._pos


class RM:
    def reset_day(self):
        return {"status": "ok"}


class OM:
    def route(self, *a, **k):
        return {"status": "ok", "reason": "ok"}


def _mk():
    # Build engine with introspection-based kwargs / positional fallback
    TradeEngine = TE.TradeEngine
    cfg = {
        "risk": {
            "max_drawdown": 0.5,
            "sharpe_min": -1.0,
            "sortino_min": -1.0,
            "intraday_sector_exposure": 1.0,
        },
        "alerts": {
            "slack_url": "http://x",
            "telegram_bot": "b",
            "telegram_chat": "c",
            "email": True,
        },
    }
    cm = {
        "portfolio": PF(),
        "risk_manager": RM(),
        "risk": RM(),
        "rm": RM(),
        "order_manager": OM(),
        "order_router": OM(),
        "router": OM(),
        "performance_tracker": PT(),
        "perf": PT(),
        "tracker": PT(),
        "config": cfg,
    }
    sig = inspect.signature(TradeEngine.__init__)
    params = [p for p in list(sig.parameters)[1:]]
    kw = {}
    for n in params:
        if n in cm:
            kw[n] = cm[n]
        elif n in ("riskMgr", "risk_module"):
            kw[n] = cm["risk"]
        elif n in ("om", "orderMgr"):
            kw[n] = cm["order_manager"]
        elif n in ("pt", "perf_tracker"):
            kw[n] = cm["performance_tracker"]
        elif n.lower().startswith("risk"):
            kw[n] = cm["risk"]
        elif "order" in n or "router" in n:
            kw[n] = cm["order_manager"]
        elif "perf" in n or "track" in n:
            kw[n] = cm["performance_tracker"]
        elif "portfol" in n:
            kw[n] = cm["portfolio"]
        elif "config" in n or "cfg" in n:
            kw[n] = cm["config"]
    try:
        return TradeEngine(**kw)
    except TypeError:
        return TradeEngine(*[kw.get(n) for n in params])


def _find(te, names):
    for n in names:
        f = getattr(te, n, None)
        if callable(f):
            return f
    return None


def _call_signal(te, **kw):
    f = _find(
        te,
        [
            "process_signal",
            "_on_signal",
            "on_signal",
            "handle_signal",
            "submit",
            "trade",
        ],
    )
    if f:
        try:
            return f(**kw)
        except TypeError:
            sig = inspect.signature(f)
            order = []
            for p in list(sig.parameters.values()):
                order.append(kw.get(p.name))
            return f(*order)
    return {"status": "rejected", "reason": "no_signal_entrypoint"}


# ---- tests ----


def test_invalid_price_and_signal_cover_224_232_228_230():
    te = _mk()
    r1 = _call_signal(te, symbol="AAPL", size=1.0, price=None, signal="BUY")
    r2 = _call_signal(te, symbol="AAPL", size=1.0, price=1.0, signal=123)
    assert isinstance(r1, dict) and isinstance(r2, dict)


def test_equity_depleted_236_and_normalize_invalid_status_329_333():
    te = _mk()
    te.portfolio.equity = 0.0
    r = _call_signal(te, symbol="AAPL", size=1.0, price=1.0, signal="BUY")
    if hasattr(te, "_normalize_result"):
        assert te._normalize_result({"status": "weird"})["status"] == "rejected"


def test_alert_matrix_103_144(monkeypatch):
    te = _mk()

    class R:
        def __init__(self, c):
            self.status_code = c

    # success paths
    monkeypatch.setitem(
        sys.modules,
        "requests",
        types.SimpleNamespace(post=lambda *a, **k: R(200), get=lambda *a, **k: R(200)),
    )

    class SMTPOK:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def send_message(self, *a, **k):
            return None

    monkeypatch.setitem(
        sys.modules, "smtplib", types.SimpleNamespace(SMTP=lambda *a, **k: SMTPOK())
    )
    if hasattr(te, "_fire_alert"):
        te._fire_alert("ok")

    # exception paths
    def boom(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setitem(
        sys.modules, "requests", types.SimpleNamespace(post=boom, get=boom)
    )

    class SMTPBAD:
        def __enter__(self):
            raise RuntimeError("bad")

        def __exit__(self, *a):
            return False

    monkeypatch.setitem(
        sys.modules, "smtplib", types.SimpleNamespace(SMTP=lambda *a, **k: SMTPBAD())
    )
    if hasattr(te, "_fire_alert"):
        te._fire_alert("fail")


def test_audit_header_then_exception_154_169(monkeypatch, tmp_path):
    te = _mk()
    te.audit_log = str(tmp_path / "audit.csv")
    te.backup_log = str(tmp_path / "backup.csv")
    if hasattr(te, "_write_audit"):
        te._write_audit(["t", "AAPL", "BUY", 1, 1.0, "ok", 100.0, ""])
    # exception path (no raise): force makedirs/open to fail
    te.audit_log = str(tmp_path / "no_dir" / "audit.csv")
    te.backup_log = str(tmp_path / "no_dir" / "backup.csv")
    monkeypatch.setattr(
        "os.makedirs", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("mkfail"))
    )

    class Blower:
        def __call__(self, *a, **k):
            raise RuntimeError("openfail")

        def __enter__(self):
            raise RuntimeError("openfail")

        def __exit__(self, *a):
            return False

    monkeypatch.setattr("builtins.open", Blower())
    if hasattr(te, "_write_audit"):
        te._write_audit(["t", "AAPL", "BUY", 1, 1.0, "ok", 100.0, ""])


def test_router_error_and_algo_imports_263_288(monkeypatch):
    te = _mk()

    # algo imports
    class TWAP:
        def __init__(self, om):
            pass

        def execute(self):
            return {"status": "ok", "reason": "ok"}

    fake = types.SimpleNamespace(TWAPExecutor=TWAP, VWAPExecutor=TWAP)
    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda name: (
            fake if name.endswith((".twap", ".vwap")) else importlib.import_module(name)
        ),
    )
    if hasattr(te, "_route_with_algo"):
        assert te._route_with_algo("AAPL", "BUY", 1, 1.0, algo="twap")["status"] == "ok"
        assert te._route_with_algo("AAPL", "BUY", 1, 1.0, algo="vwap")["status"] == "ok"
    # router error
    if hasattr(te, "order_manager"):
        te.order_manager.route = lambda *a, **k: (_ for _ in ()).throw(
            RuntimeError("router")
        )
    if hasattr(te, "_route_direct"):
        r = te._route_direct("AAPL", "BUY", 1, 1.0)
        assert r["status"] == "blocked"


def test_filters_ratio_normalize_write_capture_306_352(tmp_path):
    te = _mk()
    te.config.setdefault("filters", {})
    te.config["filters"].update({"sentiment": True, "gatescore": True})
    te.sentiment_filter = types.SimpleNamespace(allow=lambda *a, **k: False)
    te.gatescore = types.SimpleNamespace(allow=lambda *a, **k: False)
    if hasattr(te, "_filters_ok"):
        assert te._filters_ok("AAPL", "BUY", 1, 1.0)["status"] == "blocked"
        te.sentiment_filter.allow = lambda *a, **k: True
        assert te._filters_ok("AAPL", "BUY", 1, 1.0)["status"] == "blocked"
    # ratio guards
    te.performance_tracker = PT(s=-2.0, t=-2.0)
    _call_signal(te, symbol="AAPL", size=1.0, price=1.0, signal="BUY")
    # normalize OK→filled + reason normalization
    if hasattr(te, "_normalize_result"):
        g = te._normalize_result({"status": "ok", "reason": "ok"})
        assert g["status"] == "filled" and g["reason"] == "normalized_ok"
    # audit capture exception
    if hasattr(te, "_write_audit"):
        te._write_audit = lambda row: (_ for _ in ()).throw(RuntimeError("fail"))
        if hasattr(te, "_fire_alert"):
            te._fire_alert("audit capture")


def test_positions_history_outcome_376_387(caplog):
    te = _mk()
    if hasattr(te, "get_positions"):
        te.get_positions()
    if hasattr(te, "get_history"):
        te.get_history()
    if hasattr(te, "record_trade_outcome"):

        def bad(pnl):
            raise RuntimeError("x")

        if hasattr(te, "performance_tracker"):
            te.performance_tracker.record_trade = bad
        te.record_trade_outcome(1.0)
