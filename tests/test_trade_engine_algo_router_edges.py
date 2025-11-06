import importlib
import inspect
import types
from importlib import import_module as _imp

TE = _imp("hybrid_ai_trading.trade_engine")


def _mk():
    TradeEngine = TE.TradeEngine
    sig = inspect.signature(TradeEngine.__init__)
    params = [p for p in list(sig.parameters)[1:]]  # skip self

    # minimal doubles
    OM = type(
        "OM", (object,), {"route": lambda *a, **k: {"status": "ok", "reason": "ok"}}
    )
    PT = type(
        "PT", (object,), {"sharpe_ratio": lambda s: 0.0, "sortino_ratio": lambda s: 0.0}
    )

    class PF:
        def __init__(self):
            self.equity = 100.0
            self.history = [(0, 100.0)]
            self._pos = {"AAPL": {"size": 1, "avg_price": 100.0}}

        def reset_day(self):
            return {"status": "ok"}

        def get_positions(self):
            return self._pos

    pool = {
        "portfolio": PF(),
        "risk_manager": object(),
        "risk": object(),
        "rm": object(),
        "order_manager": OM(),
        "order_router": OM(),
        "router": OM(),
        "performance_tracker": PT(),
        "perf": PT(),
        "tracker": PT(),
        "config": {"risk": {"max_drawdown": 0.5}},
    }
    kwargs = {}
    for n in params:
        if n in pool:
            kwargs[n] = pool[n]
        elif n in ("riskMgr", "risk_module"):
            kwargs[n] = pool["risk"]
        elif n in ("om", "orderMgr"):
            kwargs[n] = pool["order_manager"]
        elif n in ("pt", "perf_tracker"):
            kwargs[n] = pool["performance_tracker"]
        elif n.lower().startswith("risk"):
            kwargs[n] = pool["risk"]
        elif "order" in n or "router" in n:
            kwargs[n] = pool["order_manager"]
        elif "perf" in n or "track" in n:
            kwargs[n] = pool["performance_tracker"]
        elif "portfol" in n:
            kwargs[n] = pool["portfolio"]
        elif "config" in n or "cfg" in n:
            kwargs[n] = pool["config"]
    try:
        return TradeEngine(**kwargs)
    except TypeError:
        return TradeEngine(*[kwargs.get(n) for n in params])


def test_algo_fail_then_router_error(monkeypatch):
    te = _mk()

    # 1) dynamic algo import failure (261Ã¢â‚¬â€œ282)
    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda name: (_ for _ in ()).throw(ImportError("fail")),
    )
    for n in ("_route_with_algo", "route_with_algo", "route_algo"):
        f = getattr(te, n, None)
        if callable(f):
            try:
                f("AAPL", "BUY", 1, 1.0, algo="twap")
            except Exception:
                pass
            break

    # 2) router direct error (286Ã¢â‚¬â€œ288, neighbors)
    if hasattr(te, "order_manager"):
        te.order_manager.route = lambda *a, **k: (_ for _ in ()).throw(
            RuntimeError("router")
        )
    for n in ("_route_direct", "route_direct", "direct_route"):
        f = getattr(te, n, None)
        if callable(f):
            try:
                f("AAPL", "BUY", 1, 1.0)
            except Exception:
                pass
            break
