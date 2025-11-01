"""
Unit Tests: Signals Registry (Hybrid AI Quant Pro v2.5 â€“ Hedge-Fund Grade, 100% Coverage)
----------------------------------------------------------------------------------------
Validates that the STRATEGIES registry in signals/__init__.py:
- Contains all expected keys
- Maps to callable .generate methods
- Produces valid outputs ("BUY", "SELL", "HOLD" or dict with 'signal')
- No unexpected or missing strategies
"""

import pytest

from hybrid_ai_trading.signals import STRATEGIES


def test_registry_keys_and_callables():
    expected_keys = {
        "breakout_intraday",
        "breakout_polygon",
        "breakout_v1",
        "ma",
        "rsi",
        "bollinger",
        "macd",
        "vwap",
    }
    assert (
        set(STRATEGIES.keys()) == expected_keys
    ), f"STRATEGIES keys mismatch â†’ expected {expected_keys}, got {set(STRATEGIES.keys())}"
    for name, func in STRATEGIES.items():
        assert callable(func), f"Strategy {name} is not callable"


@pytest.mark.parametrize("strategy", STRATEGIES.keys())
def test_registry_callables_return_valid(strategy):
    func = STRATEGIES[strategy]
    bars = [{"c": 100, "h": 101, "l": 99, "v": 1000}]
    result = func("AAPL", bars)
    if isinstance(result, str):
        assert result in {"BUY", "SELL", "HOLD"}
    elif isinstance(result, dict):
        assert "signal" in result
        assert result["signal"] in {"BUY", "SELL", "HOLD"}
    else:
        pytest.fail(f"{strategy} returned unexpected type: {type(result)}")
