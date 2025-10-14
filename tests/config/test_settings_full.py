import pytest
from hybrid_ai_trading.utils.config_validation import validate_config

def test_validate_ok_minimal():
    cfg = {"mode": "paper", "sentiment": {"model": "vader", "neutral_zone": 0.1}}
    out = validate_config(cfg)
    assert out["mode"] == "paper"
    assert out["sentiment"]["model"] == "vader"
    assert out["sentiment"]["neutral_zone"] == 0.1

@pytest.mark.parametrize("bad", ["oops", "BAD", "unknown"])
def test_validate_bad_model(bad):
    with pytest.raises(ValueError):
        validate_config({"mode": "paper", "sentiment": {"model": bad}})

@pytest.mark.parametrize("nz", [-0.1, 1.1])
def test_validate_bad_neutral_zone(nz):
    with pytest.raises(ValueError):
        validate_config({"mode": "paper", "sentiment": {"model": "vader", "neutral_zone": nz}})

@pytest.mark.parametrize("thr", [-0.01, 1.01])
def test_validate_bad_threshold(thr):
    with pytest.raises(ValueError):
        validate_config({"mode": "paper", "sentiment": {"model": "vader", "threshold": thr}})

@pytest.mark.parametrize("se", [0, -100])
def test_validate_bad_starting_equity(se):
    with pytest.raises(ValueError):
        validate_config({"mode": "paper", "sentiment": {"model": "vader"}, "starting_equity": se})

def test_validate_costs_nonnegative():
    out = validate_config({"mode": "paper", "sentiment": {"model": "vader"}, "costs": {"commission_pct": 0.001, "slippage_pct": 0}})
    assert out["costs"]["commission_pct"] == 0.001
    assert out["costs"]["slippage_pct"] == 0