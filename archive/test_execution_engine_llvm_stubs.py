"""
Unit Tests: ExecutionEngine LLVM Stubs (Hybrid AI Quant Pro v3.3 – Hedge Fund Grade)
-----------------------------------------------------------------------------------
Covers:
- LLVMExecutionEngine alias instantiation
- create_mcjit_compiler() raising RuntimeError
- check_jit_execution() raising RuntimeError

Ensures hedge-fund safety: JIT stubs never execute silently and always fail fast.
"""

import pytest

from hybrid_ai_trading.execution import execution_engine


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------
def test_llvm_execution_engine_alias_instantiates(config_stub):
    """
    ✅ Legacy alias instantiates and behaves like ExecutionEngine.
    Ensures alias provides portfolio tracker and risk manager in dry_run mode.
    """
    eng = execution_engine.LLVMExecutionEngine(dry_run=True, config=config_stub)
    assert eng.dry_run is True
    assert eng.portfolio_tracker is not None
    assert eng.risk_manager is not None


def test_create_mcjit_compiler_raises():
    """
    ❌ Stub must raise RuntimeError when invoked.
    Verifies hedge-fund safety: no silent fallback into JIT.
    """
    with pytest.raises(RuntimeError) as excinfo:
        execution_engine.create_mcjit_compiler("dummy_module", "dummy_tm")
    assert "not supported" in str(excinfo.value)


def test_check_jit_execution_raises():
    """
    ❌ Stub must raise RuntimeError when invoked.
    Verifies hedge-fund safety: JIT execution is explicitly blocked.
    """
    with pytest.raises(RuntimeError) as excinfo:
        execution_engine.check_jit_execution()
    assert "not supported" in str(excinfo.value)
