import pytest

from hybrid_ai_trading.execution.blockg_enforce import BlockGNotReady, require_blockg_ready_for_live


def test_require_blockg_ready_for_live_unknown_symbol_fail_closed():
    with pytest.raises(BlockGNotReady):
        require_blockg_ready_for_live("UNKNOWN", status={"as_of_date": "2099-01-01"})


def test_require_blockg_ready_for_live_blocks_when_flag_false():
    status = {
        "as_of_date": "2025-12-18",
        "nvda_blockg_ready": False,
        "reasons_not_ready": ["x"],
    }
    with pytest.raises(BlockGNotReady) as exc:
        require_blockg_ready_for_live("NVDA", status=status)
    assert "nvda_blockg_ready=false" in str(exc.value).lower()
