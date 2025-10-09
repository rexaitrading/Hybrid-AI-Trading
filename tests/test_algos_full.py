"""
Unit Tests: Algo Orchestrator
(Hybrid AI Quant Pro v3.1 – Hedge-Fund OE Grade, AAA Coverage)
----------------------------------------------------------------
Covers all branches in algos/orchestrator.py and __init__.py:

- get_algo_executor:
  * VWAP, TWAP, ICEBERG success
  * Unknown name raises KeyError + logs
- ALGO_REGISTRY: contains correct keys
- __all__: exported symbols are importable
"""

import pytest
import logging
import importlib
import hybrid_ai_trading.algos as algos


# ----------------------------------------------------------------------
# get_algo_executor success
# ----------------------------------------------------------------------
def test_get_algo_executor_success():
    """Verify supported executors resolve correctly via get_algo_executor."""
    vwap_cls = algos.get_algo_executor("vwap")
    twap_cls = algos.get_algo_executor("TWAP")
    iceberg_cls = algos.get_algo_executor("Iceberg")

    assert vwap_cls is algos.VWAPExecutor
    assert twap_cls is algos.TWAPExecutor
    assert iceberg_cls is algos.IcebergExecutor


# ----------------------------------------------------------------------
# get_algo_executor failure
# ----------------------------------------------------------------------
def test_get_algo_executor_failure(caplog):
    """Unknown executor name raises KeyError and logs error."""
    caplog.set_level(logging.ERROR)
    with pytest.raises(KeyError):
        algos.get_algo_executor("unknown123")
    assert "not found" in caplog.text.lower()


# ----------------------------------------------------------------------
# Registry consistency
# ----------------------------------------------------------------------
def test_algo_registry_contains_correct_keys():
    """Registry should contain the expected keys."""
    keys = set(algos.ALGO_REGISTRY.keys())
    assert keys == {"VWAP", "TWAP", "ICEBERG"}

    # Ensure registry resolves to the right classes through get_algo_executor
    for k in keys:
        cls = algos.get_algo_executor(k)
        assert cls.__name__.upper().startswith(k)


# ----------------------------------------------------------------------
# __all__ exports
# ----------------------------------------------------------------------
def test_all_exports_are_importable():
    """__all__ should expose valid symbols."""
    mod = importlib.import_module("hybrid_ai_trading.algos")
    for name in mod.__all__:
        assert hasattr(mod, name)
