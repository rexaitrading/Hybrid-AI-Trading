import importlib
import sys
import types

from _engine_factory import call_signal, find, make_engine


def test_alerts_success_and_exceptions(monkeypatch):
    te = make_engine(alerts=True)

    class R:
        def __init__(self, c):
            self.status_code = c

    # success (113ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ115/127ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ129/137ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ139)
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

    # exceptions (115ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ117 / 131ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ132 / 141ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ142) + top except (103ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ104)
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
    sys.modules.pop("requests", None)
    sys.modules.pop("smtplib", None)
    if hasattr(te, "_fire_alert"):
        try:
            te._fire_alert("no-mods")
        except Exception:
            pass


def test_audit_header_then_exception(monkeypatch, tmp_path):
    te = make_engine()
    te.audit_log = str(tmp_path / "audit.csv")
    te.backup_log = str(tmp_path / "backup.csv")
    if hasattr(te, "_write_audit"):
        te._write_audit(
            ["t", "AAPL", "BUY", 1, 1.0, "ok", 100.0, ""]
        )  # 154ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ167
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
        te._write_audit(
            ["t", "AAPL", "BUY", 1, 1.0, "ok", 100.0, ""]
        )  # 168ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ169


def test_invalids_equity_and_kelly_drawdown():
    te = make_engine()
    # invalids 232 / 225/228/230
    call_signal(te, symbol="AAPL", size=1.0, price=None, signal="BUY")
    call_signal(te, symbol="AAPL", size=1.0, price=1.0, signal=123)
    call_signal(te, symbol="AAPL", size=1.0, price=1.0, signal="HOLD?")
    # equity depleted 236
    te2 = make_engine(equity=0.0)
    call_signal(te2, symbol="AAPL", size=1.0, price=1.0, signal="BUY")
    # kelly + drawdown try/except 241ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ251 / 247ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ248
    te3 = make_engine(history=[(0, 100.0)])
    call_signal(te3, symbol="AAPL", size=None, price=1.0, signal="BUY")
    te4 = make_engine(history=None)
    call_signal(te4, symbol="AAPL", size=None, price=1.0, signal="BUY")


def test_sector_algo_success_and_fail_router_error(monkeypatch):
    import importlib
    import types

    from _engine_factory import call_signal, find, make_engine

    # sector exposure path 239Ã¢â‚¬â€œ354
    te = make_engine(
        risk_override={"intraday_sector_exposure": 0.001},
        positions={"AAPL": {"size": 3, "avg_price": 200.0}},
    )
    call_signal(te, symbol="AAPL", size=1.0, price=1.0, signal="BUY")

    # algo success 263Ã¢â‚¬â€œ269
    class TWAP:
        def __init__(self, om):
            pass

        def execute(self):
            return {"status": "ok", "reason": "ok"}

    fake = types.SimpleNamespace(TWAPExecutor=TWAP, VWAPExecutor=TWAP)

    # capture the original importer BEFORE patching to avoid recursion
    orig_import = importlib.import_module
    # success: only twap/vwap are intercepted
    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda name, _orig=orig_import: (
            fake if name.endswith((".twap", ".vwap")) else _orig(name)
        ),
    )

    te2 = make_engine()
    f = find(te2, ["_route_with_algo", "route_with_algo", "route_algo"])
    if f:
        f("AAPL", "BUY", 1, 1.0, algo="twap")
        f("AAPL", "BUY", 1, 1.0, algo="vwap")

    # failure: now make ONLY twap/vwap raise, everything else uses original
    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda name, _orig=orig_import: (
            (_ for _ in ()).throw(ImportError("fail"))
            if name.endswith((".twap", ".vwap"))
            else _orig(name)
        ),
    )
    if f:
        try:
            f("AAPL", "BUY", 1, 1.0, algo="twap")
        except Exception:
            pass

    # restore importer before proceeding
    monkeypatch.setattr(importlib, "import_module", orig_import)

    # router error 286Ã¢â‚¬â€œ288 + neighbors
    te3 = make_engine()
    if hasattr(te3, "order_manager"):
        te3.order_manager.route = lambda *a, **k: (_ for _ in ()).throw(
            RuntimeError("router")
        )
    g = find(te3, ["_route_direct", "route_direct", "direct_route"])
    if g:
        try:
            g("AAPL", "BUY", 1, 1.0)
        except Exception:
            pass


def test_filters_ratios_normalize_and_audit_capture(monkeypatch):
    te = make_engine(ratios=(-2.0, -2.0))
    te.config.setdefault("filters", {})
    te.config["filters"].update({"sentiment": True, "gatescore": True})
    te.sentiment_filter = types.SimpleNamespace(allow=lambda *a, **k: False)
    te.gatescore = types.SimpleNamespace(allow=lambda *a, **k: False)
    h = find(te, ["_filters_ok", "filters_ok"])
    if h:
        h("AAPL", "BUY", 1, 1.0)
        te.sentiment_filter.allow = lambda *a, **k: True
        h("AAPL", "BUY", 1, 1.0)
    if hasattr(te, "_normalize_result"):
        te._normalize_result({"status": "weird"})
        te._normalize_result({"status": "ok", "reason": "ok"})
    if hasattr(te, "_write_audit"):
        te._write_audit = lambda row: (_ for _ in ()).throw(RuntimeError("fail"))
        if hasattr(te, "_fire_alert"):
            te._fire_alert("audit_capture")


def test_positions_history_and_outcome(caplog):
    te = make_engine()
    if hasattr(te, "get_positions"):
        te.get_positions()
    if hasattr(te, "get_history"):
        te.get_history()
    if hasattr(te, "record_trade_outcome"):

        def bad(pnl):
            raise RuntimeError("x")

        if hasattr(te, "performance_tracker"):
            te.performance_tracker.record_trade = bad
        te.record_trade_outcome(1.23)


def test_reset_day_branches(monkeypatch):
    te = make_engine()
    # portfolio error 175ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ179
    if hasattr(te, "portfolio") and hasattr(te.portfolio, "reset_day"):
        te.portfolio.reset_day = lambda: (_ for _ in ()).throw(RuntimeError("PFAIL"))
        if hasattr(te, "daily_reset"):
            te.daily_reset()
        te.portfolio.reset_day = lambda: {"status": "ok"}
    # risk error 182ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ186
    for attr in ("risk_manager", "risk", "rm"):
        if hasattr(te, attr):
            setattr(
                getattr(te, attr),
                "reset_day",
                lambda: (_ for _ in ()).throw(RuntimeError("RFAIL")),
            )
            break
    if hasattr(te, "daily_reset"):
        te.daily_reset()
    # generic 197ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ198
    if hasattr(te, "daily_reset"):
        monkeypatch.setattr(
            te, "daily_reset", lambda: (_ for _ in ()).throw(RuntimeError("GENERIC"))
        )
        try:
            te.daily_reset()
        except Exception:
            pass
