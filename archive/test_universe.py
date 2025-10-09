"""
Unit Tests: Universe Definitions (Hybrid AI Quant Pro – Hedge-Fund Grade)
=========================================================================
Covers:
- groups() returns all expected keys
- Each group is a non-empty list of strings
- __all__ contains the correct exports
"""

import pytest
import hybrid_ai_trading.utils.universe as universe


def test_groups_contains_all_keys_and_types():
    g = universe.groups()
    expected_keys = ["Core_Stocks", "Core_Crypto", "Macro_Risk", "Leverage_Tools", "IPO_Watch"]

    # Check all expected keys exist
    for key in expected_keys:
        assert key in g, f"{key} missing from groups()"

    # Each value should be a non-empty list of strings
    for key, values in g.items():
        assert isinstance(values, list)
        assert all(isinstance(v, str) for v in values)
        assert values, f"{key} should not be empty"


def test_groups_dict_structure_and_equality():
    """groups() should return the same dict contents as module-level vars."""
    g = universe.groups()
    assert g["Core_Stocks"] == universe.Core_Stocks
    assert g["Core_Crypto"] == universe.Core_Crypto
    assert g["Macro_Risk"] == universe.Macro_Risk
    assert g["Leverage_Tools"] == universe.Leverage_Tools
    assert g["IPO_Watch"] == universe.IPO_Watch


def test_all_exports_are_correct():
    """__all__ must include all five groups and the groups() function."""
    expected = {"Core_Stocks", "Core_Crypto", "Macro_Risk", "Leverage_Tools", "IPO_Watch", "groups"}
    assert set(universe.__all__) == expected
