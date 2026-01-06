from __future__ import annotations

import sys
import pytest


@pytest.fixture(autouse=True)
def _restore_algos_modules():
    """
    Prevent cross-test leakage via sys.modules injection for hybrid_ai_trading.algos.*.
    Many tests replace sys.modules entries to simulate algo executors; this fixture
    snapshots and restores those entries around each test.
    """
    prefix = "hybrid_ai_trading.algos."
    before = {k: sys.modules.get(k) for k in list(sys.modules.keys()) if k.startswith(prefix)}
    yield
    # Remove new keys
    after_keys = [k for k in list(sys.modules.keys()) if k.startswith(prefix)]
    for k in after_keys:
        if k not in before:
            sys.modules.pop(k, None)
    # Restore prior objects
    for k, v in before.items():
        if v is None:
            sys.modules.pop(k, None)
        else:
            sys.modules[k] = v


@pytest.fixture()
def TradeEngineClass():
    # TODO: update import path to where TradeEngine actually lives
    from hybrid_ai_trading.trade_engine import TradeEngine
    return TradeEngine
# ----------------------------------------------------------------------
# Block-G contract stub guard (suite determinism)
# ----------------------------------------------------------------------
from pathlib import Path
import subprocess

@pytest.fixture(autouse=True)
def _ensure_blockg_status_stub_exists():
    """
    Some tests/tools clean logs/ during the suite. This ensures the Block-G
    contract stub exists whenever tests rely on it.
    """
    repo_root = Path(__file__).resolve().parents[1]
    logs_dir = repo_root / "logs"
    stub = logs_dir / "blockg_status_stub.json"

    if not stub.exists():
        logs_dir.mkdir(parents=True, exist_ok=True)
        ps1 = repo_root / "tools" / "Build-BlockGStatusStub.ps1"
        if ps1.exists():
            subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1)],
                cwd=str(repo_root),
                capture_output=True,
                text=True,
            )
    yield
