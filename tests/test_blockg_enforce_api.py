def test_blockg_enforce_imports_clean():
    from hybrid_ai_trading.execution import blockg_enforce  # noqa: F401

def test_blockg_contract_exports_symbol_gate():
    from hybrid_ai_trading.execution import blockg_contract
    assert hasattr(blockg_contract, "ensure_symbol_blockg_ready")
