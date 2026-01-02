import os

from hybrid_ai_trading.phase7.preflight_gate import _phase7_require_blockg


def test_phase7_requires_blockg_when_live_intent_env_set(monkeypatch):
    # Even if someone tries to disable it, live intent must force BlockG.
    monkeypatch.setenv("HAT_IS_PAPER", "0")
    monkeypatch.setenv("HAT_PHASE7_REQUIRE_BLOCKG", "0")
    assert _phase7_require_blockg() is True


def test_phase7_allows_disable_only_when_offline(monkeypatch):
    # Offline analytics may allow turning it off explicitly.
    monkeypatch.delenv("HAT_IS_PAPER", raising=False)
    monkeypatch.delenv("HAT_PHASE7_LIVE_SCALING", raising=False)
    monkeypatch.setenv("HAT_PHASE7_REQUIRE_BLOCKG", "0")
    assert _phase7_require_blockg() is False
