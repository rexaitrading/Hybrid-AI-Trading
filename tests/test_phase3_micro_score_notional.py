from hybrid_ai_trading.replay.edge_model_v0 import Bar
from hybrid_ai_trading.replay.edge_model_v2 import score_signals_v2

def _mk_bars(n=120, base=688.0):
    bars=[]
    # timestamps match your IB-style (two spaces), and are within the SPY RTH window you fetch (06:30-12:59)
    # We'll keep them simple; only parsing & ordering matters.
    hh=6; mm=30
    for i in range(n):
        ts=f"20260106  {hh:02d}:{mm:02d}:00"
        px=base + (i * 0.02)
        bars.append(Bar(ts=ts, o=px, h=px+0.05, l=px-0.05, c=px+0.01, v=1000.0))
        mm += 1
        if mm >= 60:
            mm = 0
            hh += 1
    return bars

def test_micro_score_not_always_zero():
    bars=_mk_bars()
    # Force one signal; function will compute shares, slip, fees, etc.
    out = score_signals_v2(bars, [10])
    assert isinstance(out, list)
    assert len(out) >= 1
    ms = float(out[0].get("micro_score", 0.0) or 0.0)
    assert ms > 0.0
