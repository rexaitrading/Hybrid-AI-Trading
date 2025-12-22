from __future__ import annotations

import subprocess
import sys
from pathlib import Path

def test_phase1_backtest_replay_smoke(tmp_path: Path):
    inp = Path("tests/_fixtures/phase1_tiny.csv")
    assert inp.exists()

    p = subprocess.run(
        [sys.executable, "runners/backtest_replay.py", "--input", str(inp), "--batch", "2", "--log", str(tmp_path/"bt.jsonl")],
        capture_output=True,
        text=True,
    )
    # Accept exit 0 (decisions found) or 2 (fail-closed: no decisions)
    assert p.returncode in (0, 2)
    assert '"summary"' in (p.stdout or "")
