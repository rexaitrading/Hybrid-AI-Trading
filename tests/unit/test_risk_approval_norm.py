try:
    from hybrid_ai_trading.runners.paper_quantcore import _norm_approval
except Exception:
    # In case import path changed; fallback from trader helper
    from hybrid_ai_trading.runners.paper_trader import _norm_approval

def test_norm_approval_dict():
    assert _norm_approval({"approved": True, "reason": "ok"}) == {"approved": True, "reason":"ok"}

def test_norm_approval_tuple():
    assert _norm_approval((True,"")) == {"approved": True, "reason":""}

def test_norm_approval_bool():
    assert _norm_approval(True) == {"approved": True, "reason":""}
