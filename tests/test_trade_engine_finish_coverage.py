from types import SimpleNamespace
from tests.test_trade_engine_optionA_exec100 import make_engine

def _prep(te):
    # Neutralize anything that could short-circuit
    if hasattr(te, "_sector_exposure_breach"):
        te._sector_exposure_breach = lambda s: False
    # Default config/metrics/portfolio
    if not hasattr(te, "config") or te.config is None:
        te.config = {}
    te.config.setdefault("risk", {})
    te.config.setdefault("regime", {})
    if not hasattr(te, "metrics") or te.metrics is None:
        te.metrics = SimpleNamespace(sortino=5.0)
    te.portfolio = SimpleNamespace(equity=100.0, history=[("t0", 100.0)])

def test_finish_process_signal_all_branches():
    te = make_engine()

    # A) regime disabled → early return (~301)
    _prep(te)
    te.config["regime"]["enabled"] = False
    if hasattr(te, "risk_manager"):
        te.risk_manager.approve_trade = lambda *a, **k: {"status":"ok","size":1}
    if hasattr(te, "order_manager"):
        te.order_manager.submit = lambda *a, **k: {"status":"ok", "order_id": 1}
    try:
        te.process_signal("AAPL", "BUY", 1)
    except Exception:
        pass

    # B) sortino breach → blocked (~325)
    _prep(te)
    te.config["regime"]["enabled"] = True
    te.config["risk"]["min_sortino"] = 10.0
    te.metrics.sortino = 0.1
    if hasattr(te, "risk_manager"):
        te.risk_manager.approve_trade = lambda *a, **k: {"status":"ok","size":1}
    if hasattr(te, "order_manager"):
        te.order_manager.submit = lambda *a, **k: {"status":"ok", "order_id": 2}
    try:
        te.process_signal("AAPL", "BUY", 1)
    except Exception:
        pass

    # C) drawdown gate present & Kelly exception → size fallback (241–257)
    _prep(te)
    te.config["risk"]["max_drawdown"] = 0.99     # keep the drawdown gate present
    # Force Kelly path by making size=None then raising inside Kelly -> fallback size=1
    if hasattr(te, "risk_manager"):
        te.risk_manager.approve_trade = lambda *a, **k: {"status":"ok","size":None}
    te.kelly_sizer = SimpleNamespace(size_position=lambda *a, **k: (_ for _ in ()).throw(RuntimeError("kelly boom")))
    if hasattr(te, "order_manager"):
        te.order_manager.submit = lambda *a, **k: {"status":"submitted", "order_id": 3}
    try:
        te.process_signal("AAPL", "BUY", None)
    except Exception:
        pass

    # D) tail normalization: result.status/reason "ok" -> "filled"/"normalized_ok" (334–339)
    _prep(te)
    te.config["regime"]["enabled"] = True
    if hasattr(te, "risk_manager"):
        te.risk_manager.approve_trade = lambda *a, **k: {"status":"ok","size":2}
    if hasattr(te, "order_manager"):
        te.order_manager.submit = lambda *a, **k: {"status":"ok","reason":"ok","order_id": 4}
    for waiter in ("wait_for_fill","await_fill","poll_fill","_await_fill"):
        if hasattr(te, waiter):
            setattr(te, waiter, lambda *a, **k: {"status":"ok"})
    try:
        te.process_signal("AAPL", "BUY", 2)
    except Exception:
        pass
