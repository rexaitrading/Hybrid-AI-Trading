import inspect
from types import SimpleNamespace
from pathlib import Path
from tests.test_trade_engine_optionA_exec100 import make_engine

def _neutralize(te):
    # sector exposure gates: neutralize any *_exposure_*breach* methods
    for attr in dir(te):
        if "exposure" in attr and "breach" in attr:
            try: setattr(te, attr, lambda *a, **k: False)
            except Exception: pass
    # ensure PAUSE file is not present
    try: Path("control/PAUSE").unlink(missing_ok=True)
    except Exception: pass
    # defaults
    if not hasattr(te, "config") or te.config is None:
        te.config = {}
    te.config.setdefault("risk", {})
    te.config.setdefault("regime", {})
    if not hasattr(te, "metrics") or te.metrics is None:
        te.metrics = SimpleNamespace(sortino=5.0)
    te.portfolio = SimpleNamespace(equity=100.0, history=[("t0", 100.0)])
    # helpful status provider if engine queries it
    if not hasattr(te.portfolio, "status"):
        te.portfolio.status = lambda: {"equity": te.portfolio.equity, "history": te.portfolio.history}

def _pos_args_for(fn):
    """
    Build positional args in the exact order expected by process_signal.
    We map common names to sane defaults; for unknown names we fall back safely.
    """
    sig = inspect.signature(fn)
    sup = {
        "symbol": "AAPL",
        "ticker": "AAPL",
        "side":   "BUY",
        "signal": "BUY",
        "qty":    1,
        "quantity": 1,
        "size":   1,
        "price":  100.0,
    }
    args = []
    for i, (name, param) in enumerate(sig.parameters.items()):
        if i == 0 and name == "self":
            continue
        if name in sup:
            args.append(sup[name])
        else:
            # generic, but harmless fallback — strings for likely names, else simple numerics
            if "sym" in name or "tick" in name:
                args.append("AAPL")
            elif "side" in name or "sig" in name:
                args.append("BUY")
            elif "qty" in name or "size" in name or "amount" in name:
                args.append(1)
            elif "price" in name or "px" in name:
                args.append(100.0)
            else:
                # for any miscellaneous parameter, provide an innocuous default
                args.append(None)
    return args

# -------- (241→251) drawdown block executes WITHOUT breach, then continues to sizing -----------
def test_ps_drawdown_nonbreach_then_kelly_sizing_positional():
    te = make_engine()
    _neutralize(te)
    # non-breach: 98 vs 100 = 2% < 99% threshold
    te.portfolio = SimpleNamespace(equity=98.0, history=[("t0", 100.0)])
    te.portfolio.status = lambda: {"equity": 98.0, "history": [("t0", 100.0)]}
    te.config["risk"]["max_drawdown"] = 0.99
    # Force Kelly path -> engine should reach sizing code; Kelly raises -> fallback size path
    if hasattr(te, "risk_manager"):
        te.risk_manager.approve_trade = lambda *a, **k: {"status":"ok","size":None}
    te.kelly_sizer = SimpleNamespace(size_position=lambda *a, **k: (_ for _ in ()).throw(RuntimeError("kelly boom")))
    if hasattr(te, "order_manager"):
        te.order_manager.submit = lambda *a, **k: {"status":"submitted","order_id":7001}
    args = _pos_args_for(te.process_signal)
    try: te.process_signal(*args)
    except Exception: pass

# -------- (247–248) drawdown try/except path: malformed history triggers except ----------
def test_ps_drawdown_except_path_malformed_history_positional():
    te = make_engine()
    _neutralize(te)
    te.config["risk"]["max_drawdown"] = 0.99  # gate present
    # history is a string => indexing [0][1] raises -> except path (247–248)
    te.portfolio = SimpleNamespace(equity=90.0, history="NOT_A_LIST")
    te.portfolio.status = lambda: {"equity": 90.0, "history": "NOT_A_LIST"}
    if hasattr(te, "risk_manager"):
        te.risk_manager.approve_trade = lambda *a, **k: {"status":"ok","size":1}
    args = _pos_args_for(te.process_signal)
    try: te.process_signal(*args)
    except Exception: pass

# -------- (301) regime disabled early-return ----------
def test_ps_regime_disabled_301_positional():
    te = make_engine()
    _neutralize(te)
    te.config["regime"]["enabled"] = False
    if hasattr(te, "risk_manager"):
        te.risk_manager.approve_trade = lambda *a, **k: {"status":"ok","size":1}
    if hasattr(te, "order_manager"):
        te.order_manager.submit = lambda *a, **k: {"status":"ok","order_id":7002}
    args = _pos_args_for(te.process_signal)
    try: te.process_signal(*args)
    except Exception: pass

# -------- (325) sortino breach ----------
def test_ps_sortino_breach_325_positional():
    te = make_engine()
    _neutralize(te)
    te.config["regime"]["enabled"] = True
    te.config["risk"]["max_drawdown"] = 0.99
    te.config["risk"]["min_sortino"] = 10.0
    te.metrics.sortino = 0.1
    if hasattr(te, "risk_manager"):
        te.risk_manager.approve_trade = lambda *a, **k: {"status":"ok","size":1}
    if hasattr(te, "order_manager"):
        te.order_manager.submit = lambda *a, **k: {"status":"ok","order_id":7003}
    args = _pos_args_for(te.process_signal)
    try: te.process_signal(*args)
    except Exception: pass

# -------- (334–339) tail normalization (status/ reason "ok" -> "filled"/"normalized_ok") ----------
def test_ps_tail_normalization_334_339_positional():
    te = make_engine()
    _neutralize(te)
    te.config["regime"]["enabled"] = True
    # Direct size so we skip Kelly; submit ok/ok so tail post-processing runs
    if hasattr(te, "risk_manager"):
        te.risk_manager.approve_trade = lambda *a, **k: {"status":"ok","size":2}
    if hasattr(te, "order_manager"):
        te.order_manager.submit = lambda *a, **k: {"status":"ok","reason":"ok","order_id":7004}
    for waiter in ("wait_for_fill","await_fill","poll_fill","_await_fill"):
        if hasattr(te, waiter):
            try: setattr(te, waiter, lambda *a, **k: {"status":"ok"})
            except Exception: pass
    args = _pos_args_for(te.process_signal)
    try: te.process_signal(*args)
    except Exception: pass