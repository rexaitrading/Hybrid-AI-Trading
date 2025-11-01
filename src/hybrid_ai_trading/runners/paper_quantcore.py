def _norm_approval(a):
    # Accept dict / tuple / list / bool, normalize to {"approved": bool, "reason": str}
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


# QuantCore (paper) ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ minimal, stable


def evaluate(symbol, price_map, risk_mgr):
    """Return a decision bundle for the symbol (stub regime/sentiment/kelly).
    Ensures RiskManager.approve_trade is called safely regardless of signature.
    """
    # stubs for now
    regime = {"regime": "neutral", "confidence": 0.5, "reason": "stub"}
    sentiment = {"sentiment": 0.0, "confidence": 0.5, "reason": "stub"}
    sizing = {"f": 0.05, "qty": 1, "reason": "stub"}

    import inspect

    side = "BUY"  # TODO: wire real side when signals are ready
    qty = (sizing or {}).get("qty", 0) or 0
    try:
        px = float((price_map or {}).get(symbol) or 0.0)
    except Exception:
        px = 0.0
    notional = (qty or 0) * (px or 0.0)

    approval = {"approved": False, "reason": "risk_method_missing"}
    try:
        if hasattr(risk_mgr, "approve_trade"):
            sig = inspect.signature(risk_mgr.approve_trade)
            kw = {
                "symbol": symbol,
                "side": side,
                "qty": qty,
                "notional": notional,
                "price": px,
            }
            fkw = {k: v for k, v in kw.items() if k in sig.parameters}
            if fkw:
                approval = risk_mgr.approve_trade(**fkw)
            else:
                # fallback positional styles
                try:
                    approval = risk_mgr.approve_trade(side, qty, notional)
                except TypeError:
                    approval = risk_mgr.approve_trade(symbol, side, qty, notional)
        else:
            approval = {"approved": False, "reason": "risk_method_missing"}
    except TypeError as e2:
        approval = {"approved": False, "reason": f"risk_call_failed: {e2}"}
    except Exception as e:
        approval = {"approved": False, "reason": f"risk_call_failed: {e}"}

    return {
        "regime": regime,
        "sentiment": sentiment,
        "kelly_size": sizing,
        "risk_approved": _norm_approval(approval),
    }


def run_once(symbols, price_map, risk_mgr):
    """Evaluate a list/iterable of symbols and return a list of {symbol, decision}."""
    out = []
    for sym in list(symbols or []):
        out.append({"symbol": sym, "decision": evaluate(sym, price_map, risk_mgr)})
    return out
