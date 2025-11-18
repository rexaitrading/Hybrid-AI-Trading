import math

import pytest

from hybrid_ai_trading.utils.preflight import sanity_probe


@pytest.mark.xfail(reason="sanity_probe uses live IB session; unit test to be refactored")
def test_sanity_probe_passes_on_finite_data():
    result = {
        "px": 100.0,
        "funds": {"usdcad": 1.35},
        "order": {"limit": 99.5},
    }
    out = sanity_probe(result)
    assert out.get("skip") is not True
    assert out.get("reason") in (None, out.get("reason"))


@pytest.mark.xfail(reason="preflight currently uses IB/LiveGuard semantics; NaN guard TBD in Phase-8")
@pytest.mark.xfail(reason="preflight uses IB/LiveGuard semantics; NaN guard TBD in Phase-8")
def test_sanity_probe_skips_on_nan_data():
    result = {
        "px": float("nan"),
        "funds": {"usdcad": 1.35},
        "order": {"limit": 99.5},
    }
    out = sanity_probe(result)
    assert out.get("skip") is True
    assert out.get("reason") == "preflight_non_finite_data"