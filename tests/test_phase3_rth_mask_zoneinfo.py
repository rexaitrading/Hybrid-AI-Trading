from types import SimpleNamespace

def test_rth_mask_import_and_run_smoke():
    from hybrid_ai_trading.replay.edge_model_v2 import _rth_mask
    # minimal bar shape used by _rth_mask: b.ts
    bars = [SimpleNamespace(ts="20260106  06:30:00")]
    out = _rth_mask(bars)
    assert isinstance(out, list)
    assert len(out) == 1
