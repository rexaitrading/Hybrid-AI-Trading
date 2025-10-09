"""
Unit Tests: Universe Definitions (Hybrid AI Quant Pro – Hedge-Fund Grade)
Covers:
- groups() returns all expected keys
- Each group is a non-empty list of strings
- groups() output equals module-level lists
- __all__ contains the correct exports and all names are accessible
"""

import hybrid_ai_trading.utils.universe as universe


def test_groups_contains_all_keys_and_types():
    g = universe.groups()
    expected_keys = ["Core_Stocks", "Core_Crypto", "Macro_Risk", "Leverage_Tools", "IPO_Watch"]
    # Every key present
    for key in expected_keys:
        assert key in g, f"{key} missing from groups()"
    # Every value is a non-empty list of strings
    for key, values in g.items():
        assert isinstance(values, list)
        assert values, f"{key} should not be empty"
        assert all(isinstance(v, str) for v in values)


def test_groups_dict_structure_and_equality():
    g = universe.groups()
    assert g["Core_Stocks"] == universe.Core_Stocks
    assert g["Core_Crypto"] == universe.Core_Crypto
    assert g["Macro_Risk"] == universe.Macro_Risk
    assert g["Leverage_Tools"] == universe.Leverage_Tools
    assert g["IPO_Watch"] == universe.IPO_Watch


def test_all_exports_are_correct_and_accessible():
    expected = {"Core_Stocks", "Core_Crypto", "Macro_Risk", "Leverage_Tools", "IPO_Watch", "groups"}
    assert set(universe.__all__) == expected
    # Touch every exported symbol to ensure the assignments are counted by coverage
    for name in universe.__all__:
        getattr(universe, name)
