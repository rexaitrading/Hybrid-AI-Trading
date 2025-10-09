from hybrid_ai_trading.broker.ib_safe import marketable_limit
import pytest

@pytest.mark.parametrize("side,ref,ah,exp", [
    ("BUY", 100.0, True, 101.0),
    ("SELL",100.0, True, 99.0),
    ("BUY", 100.0, False,100.1),
    ("SELL",100.0, False,99.9),
])
def test_marketable_limit_values(side, ref, ah, exp):
    assert marketable_limit(side, ref, ah) == pytest.approx(exp, 1e-6)

@pytest.mark.parametrize("bad", [0.0, -1.0])
def test_marketable_limit_bad_ref(bad):
    with pytest.raises(ValueError):
        marketable_limit("BUY", bad, True)

def test_marketable_limit_bad_side():
    with pytest.raises(ValueError):
        marketable_limit("HOLD", 100.0, True)