from __future__ import annotations

import subprocess
import sys
from pathlib import Path

def test_phase1_backtest_replay_smoke(tmp_path: Path):
    # Write a tiny CSV inside tmp_path (CI-safe; no repo fixture files)
    inp = tmp_path / "phase1_tiny.csv"
    inp.write_text(
        "ts,symbol,price\n"
        "2025-12-22T09:30:00Z,NVDA,100\n"
        "2025-12-22T09:30:01Z,NVDA,100.1\n"
        "2025-12-22T09:30:02Z,NVDA,100.2\n",
        encoding="utf-8",
    )

    p = subprocess.run(
        [sys.executable, "runners/backtest_replay.py", "--input", str(inp), "--batch", "2", "--log", str(tmp_path/"bt.jsonl")],
        capture_output=True,
        text=True,
    )
    # Accept exit 0 (decisions found) or 2 (fail-closed: no decisions)
    assert p.returncode in (0, 2)
    assert '"summary"' in (p.stdout or "")
