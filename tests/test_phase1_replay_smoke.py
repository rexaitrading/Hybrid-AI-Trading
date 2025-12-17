import os
from pathlib import Path

import pytest


@pytest.fixture()
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_phase1_replay_fixture_exists(repo_root: Path):
    fx = repo_root / "tests" / "fixtures" / "nvda_1min_fullsession.csv"
    assert fx.exists(), f"Missing fixture: {fx}"


def test_phase1_nvda_bplus_gate_score_runs(repo_root: Path, monkeypatch):
    # Deterministic replay input
    fx = repo_root / "tests" / "fixtures" / "nvda_1min_fullsession.csv"
    monkeypatch.setenv("HAT_NVDA_REPLAY_CSV", str(fx))

    # Import after env is set
    from hybrid_ai_trading.replay import nvda_bplus_gate_score as mod

    # main() should be callable; must not raise
    assert hasattr(mod, "main"), "nvda_bplus_gate_score.py must expose main(); available callables=" + ",".join([n for n in dir(mod) if callable(getattr(mod,n))])
    rc = mod.main()
    assert isinstance(rc, int)
    assert rc == 0


def test_phase1_bar_replay_api_imports():
    # Basic import sanity for Phase-1 public API
    from hybrid_ai_trading.tools import bar_replay as br

    assert hasattr(br, "run_replay")
    assert hasattr(br, "load_bars")

