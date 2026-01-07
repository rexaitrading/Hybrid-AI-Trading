def test_phase6_imports():
    import hybrid_ai_trading.phase6  # package import

def test_readiness_snapshot_module_imports():
    import hybrid_ai_trading.phase6.readiness_snapshot as rs
    assert rs is not None
