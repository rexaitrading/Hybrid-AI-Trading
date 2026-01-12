import pytest

import hybrid_ai_trading.execution.blockg_ps_checker as mod
from hybrid_ai_trading.execution.blockg_errors import BlockGNotReady


def test_check_blockg_diagnostic_ok_passes_market_and_accepts_exit10(monkeypatch):
    """
    A3: check_blockg_diagnostic_ok must pass Market through and accept ps_checker_exit=10 only.
    """
    calls = {"market": None, "build": None}

    def fake_require(symbol: str, *, market=None, build=False, timeout_s=30):
        calls["market"] = market
        calls["build"] = build
        # Simulate closed-day diagnostic OK (PS returns 10; strict wrapper raises with token)
        raise BlockGNotReady("BLOCK-G FAIL-CLOSED: ps_checker_exit=10 symbol=NVDA")

    monkeypatch.setattr(mod, "require_blockg_ready_via_powershell", fake_require)

    # Should not raise (exit=10 accepted by diagnostic helper)
    mod.check_blockg_diagnostic_ok("NVDA", market="HK", build=True)

    assert calls["market"] == "HK"
    assert calls["build"] is True


def test_check_blockg_diagnostic_ok_rejects_exit2(monkeypatch):
    """
    Diagnostic helper must NOT accept exit=2.
    """
    def fake_require(symbol: str, *, market=None, build=False, timeout_s=30):
        raise BlockGNotReady("BLOCK-G FAIL-CLOSED: ps_checker_exit=2 symbol=NVDA\n[BLOCKG] NOT READY: market_session_closed_now=true")

    monkeypatch.setattr(mod, "require_blockg_ready_via_powershell", fake_require)

    with pytest.raises(BlockGNotReady):
        mod.check_blockg_diagnostic_ok("NVDA", market="HK", build=True)
