import pytest
import math
import hybrid_ai_trading.algos.vwap as mod


def make_bars(prices, vols=None):
    if vols is None:
        vols = [1] * len(prices)
    return [{"c": p, "v": v} for p, v in zip(prices, vols)]


# -------------------- Guard paths --------------------
def test_guard_empty_list():
    assert mod.vwap_signal([]) == "HOLD"            # Guard 1


def test_guard_missing_c_or_v():
    assert mod.vwap_signal([{"v": 1}]) == "HOLD"    # Guard 2 (missing c)
    assert mod.vwap_signal([{"c": 1}]) == "HOLD"    # Guard 2 (missing v)


def test_guard_non_numeric_values():
    # bad str
    assert mod.vwap_signal([{"c": "oops", "v": 1}]) == "HOLD"   # Guard 3
    # bad type
    assert mod.vwap_signal([{"c": {"x":1}, "v": 1}]) == "HOLD"  # Guard 3


def test_guard_nan_values():
    assert mod.vwap_signal([{"c": math.nan, "v": 1}]) == "HOLD" # Guard 4 (NaN close)
    assert mod.vwap_signal([{"c": 1, "v": math.nan}]) == "HOLD" # Guard 4 (NaN vol)


def test_guard_total_volume_non_positive():
    assert mod.vwap_signal([{"c": 100, "v": 0}, {"c": 101, "v": 0}]) == "HOLD"  # Guard 5


# -------------------- Decision paths --------------------
def test_tie_branch_hold():
    # VWAP = (100*1 + 200*1 + 150*2)/4 = 150; last = 150 -> HOLD
    bars = [{"c": 100, "v": 1}, {"c": 200, "v": 1}, {"c": 150, "v": 2}]
    assert mod.vwap_signal(bars) == "HOLD"


def test_buy_path():
    # VWAP ~ 100, last 120 -> BUY
    bars = make_bars([100, 100, 120], [10, 10, 10])
    assert mod.vwap_signal(bars) == "BUY"


def test_sell_path():
    # VWAP ~ 110, last 100 -> SELL
    bars = make_bars([120, 110, 100], [10, 10, 10])
    assert mod.vwap_signal(bars) == "SELL"


# -------------------- Class wrapper + __all__ --------------------
def test_vwapalgo_wrapper_and_public_api():
    algo = mod.VWAPAlgo()
    bars = make_bars([100, 105, 110], [1, 1, 1])
    assert algo.generate("AAPL", bars) in ("BUY", "SELL", "HOLD")
    # public API
    assert set(mod.__all__) == {"vwap_algo", "VWAPAlgo", "vwap_signal"}
