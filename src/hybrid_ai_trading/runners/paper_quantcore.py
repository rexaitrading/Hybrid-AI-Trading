from __future__ import annotations

from typing import Any, Dict

from hybrid_ai_trading.risk.dummy_risk import DummyRiskMgr


def _norm_approval(a):
    """Accept dict/tuple/list/bool; normalize to {'approved': bool, 'reason': str}."""
    try:
        if isinstance(a, dict):
            return {
                "approved": bool(a.get("approved")),
                "reason": str(a.get("reason", "")),
            }
        if isinstance(a, (tuple, list)) and a:
            ok = bool(a[0])
            rs = "" if len(a) < 2 else str(a[1])
            return {"approved": ok, "reason": rs}
        if isinstance(a, bool):
            return {"approved": a, "reason": ""}
    except Exception:
        pass
    return {"approved": False, "reason": "normalize_error"}


# QuantCore (paper) - minimal, stable


def _ensure_risk_mgr(risk_mgr):
    """Return a risk manager that has approve_trade(symbol, side, qty, notional)."""
    try:
        if hasattr(risk_mgr, "approve_trade") and callable(
            getattr(risk_mgr, "approve_trade")
        ):
            return risk_mgr
    except Exception:
        pass
    try:
        return DummyRiskMgr()  # default approve-all
    except Exception:
        import types as _t

        return _t.SimpleNamespace(
            approve_trade=lambda *a, **k: {"approved": True, "reason": "stub"}
        )


def evaluate(symbol: str, price_map: Dict[str, Any], risk_mgr) -> Dict[str, Any]:
    """Return a decision bundle for the symbol (stubbed regime/sentiment/kelly) and risk approval."""
    regime = {"regime": "neutral", "confidence": 0.5, "reason": "stub"}
    sentiment = {"sentiment": 0.0, "confidence": 0.5, "reason": "stub"}
    sizing = {"f": 0.05, "qty": 1, "reason": "stub"}

    side = "BUY"  # TODO: wire real side when signals are ready
    qty = int((sizing or {}).get("qty", 0) or 0)
    try:
        px = float((price_map or {}).get(symbol) or 0.0)
    except Exception:
        px = 0.0
    notional = float(qty) * px

    approval = {"approved": False, "reason": "risk_method_missing"}
    try:
        if hasattr(risk_mgr, "approve_trade") and callable(
            getattr(risk_mgr, "approve_trade")
        ):
            try:
                approval = risk_mgr.approve_trade(
                    symbol=symbol, side=side, qty=qty, notional=notional, price=px
                )
            except TypeError:
                try:
                    approval = risk_mgr.approve_trade(symbol, side, qty, notional)
                except TypeError:
                    approval = risk_mgr.approve_trade(side, qty, notional)
    except Exception as e:
        approval = {"approved": False, "reason": f"risk_call_failed:{e}"}

    return {
        "regime": regime,
        "sentiment": sentiment,
        "kelly_size": sizing,
        "risk_approved": _norm_approval(approval),
    }


def run_once(symbols, price_map, risk_mgr):
    """Evaluate a list of symbols and return [{'symbol':..., 'decision':{...}}, ...]."""
    rm = _ensure_risk_mgr(risk_mgr)
    out = []
    for sym in list(symbols or []):
        out.append({"symbol": sym, "decision": evaluate(sym, price_map or {}, rm)})
    return out
