import sys, os
import pytest

# --- Fix import path so Python can find utils/ ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils import universe


def test_core_stocks_defined():
    """Core_Stocks should be a non-empty collection"""
    assert universe.Core_Stocks is not None
    assert isinstance(universe.Core_Stocks, (list, dict, set))
    assert len(universe.Core_Stocks) > 0


def test_crypto_signal_defined():
    """Crypto_Signal should not be None"""
    assert universe.Crypto_Signal is not None


def test_macro_risk_defined():
    """Macro_Risk should not be None"""
    assert universe.Macro_Risk is not None


def test_leverage_tools_defined():
    """Leverage_Tools should not be None"""
    assert universe.Leverage_Tools is not None


def test_ipo_watch_defined():
    """IPO_Watch should not be None"""
    assert universe.IPO_Watch is not None


def test_groups_returns_dict():
    """groups() should return a dict with at least one key"""
    result = universe.groups()
    assert isinstance(result, dict)
    assert len(result) > 0
    # sanity check that groups has expected keys
    assert any(k in result for k in ["stocks", "crypto", "macro", "ipo"])
