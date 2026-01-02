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



# GateScore metric extraction (best-effort). Defaults to zeros (fail-closed).
def _extract_gatescore_metrics(decision):
    edge_ratio = 0.0
    micro_score = 0.0
    pnl_samples = 0
    if decision is None:
        return edge_ratio, micro_score, pnl_samples
    if isinstance(decision, dict):
        for k in ('edge_ratio','mean_edge_ratio','gatescore_edge','edge'):
            if k in decision:
                try: edge_ratio = float(decision.get(k) or 0.0)
                except Exception: pass
                break
        for k in ('micro_score','mean_micro_score','gatescore_micro','micro'):
            if k in decision:
                try: micro_score = float(decision.get(k) or 0.0)
                except Exception: pass
                break
        for k in ('pnl_samples','pnlSamples','samples','sample_count','trades_n','trade_count'):
            if k in decision:
                try: pnl_samples = int(decision.get(k) or 0)
                except Exception: pass
                break
        return edge_ratio, micro_score, pnl_samples
    # object attribute extraction
    for k in ('edge_ratio','mean_edge_ratio','gatescore_edge','edge'):
        try:
            if hasattr(decision, k):
                edge_ratio = float(getattr(decision, k) or 0.0)
                break
        except Exception:
            pass
    for k in ('micro_score','mean_micro_score','gatescore_micro','micro'):
        try:
            if hasattr(decision, k):
                micro_score = float(getattr(decision, k) or 0.0)
                break
        except Exception:
            pass
    for k in ('pnl_samples','pnlSamples','samples','sample_count','trades_n','trade_count'):
        try:
            if hasattr(decision, k):
                pnl_samples = int(getattr(decision, k) or 0)
                break
        except Exception:
            pass
    return edge_ratio, micro_score, pnl_samples

def run_once(symbols, price_map, risk_mgr):
    """Evaluate a list of symbols and return [{'symbol':..., 'decision':{...}}, ...]."""
    rm = _ensure_risk_mgr(risk_mgr)
    out = []
    for sym in list(symbols or []):
        decision = evaluate(sym, price_map or {}, rm)
        edge_ratio, micro_score, pnl_samples = _extract_gatescore_metrics(decision)
        out.append({
            'symbol': sym,
            'decision': decision,
            'edge_ratio': edge_ratio,
            'micro_score': micro_score,
            'pnl_samples': pnl_samples,
        })
    return out
