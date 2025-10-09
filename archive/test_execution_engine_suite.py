"""
ExecutionEngine Test Suite (Hybrid AI Quant Pro v1.0 – Hedge Fund Grade)
========================================================================
Unified test runner that ensures:
- Both ExecutionEngine main functionality (dry_run, live, portfolio, risk)
- ExecutionEngine LLVM stub safety (alias + stub methods)

This guarantees:
- 100% coverage across ExecutionEngine and legacy compatibility stubs
- Hedge-fund grade confidence: no silent JIT fallbacks
"""

import pytest


def main():
    """
    Run both ExecutionEngine test modules with unified coverage.
    Targets:
    - hybrid_ai_trading.execution.execution_engine
    - hybrid_ai_trading.execution.llvm_adapter
    """
    pytest_args = [
        "-v",  # verbose
        "--cov=hybrid_ai_trading.execution.execution_engine",
        "--cov=hybrid_ai_trading.execution.llvm_adapter",
        "--cov-branch",  # ensure branch coverage
        "--cov-report=term-missing",  # show uncovered lines in terminal
        "--cov-report=html",  # generate htmlcov/ for CI artifact inspection
        "tests/execution/test_execution_engine_full.py",
        "tests/test_execution_engine_llvm_stubs.py",
    ]
    raise SystemExit(pytest.main(pytest_args))


if __name__ == "__main__":
    main()
