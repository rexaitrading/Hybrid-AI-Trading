import json
import subprocess
import sys
from pathlib import Path
import csv


def test_nvda_replay_demo_creates_summary(tmp_path, monkeypatch):
    """
    Phase-1: NVDA bar replay -> EV summary JSON smoke test.

    - Uses existing data/NVDA_1m.csv
    - Calls tools/run_bar_replay_to_json.py
    - Asserts replay_summary_NVDA_<session>.json is created and has EV stats.
    """
    repo_root = Path(__file__).resolve().parents[1]
    tools_dir = repo_root / "tools"
    data_dir = repo_root / "data"
    sample_csv = data_dir / "NVDA_1m.csv"

    if not sample_csv.exists():
        # CI-safe: generate a tiny synthetic CSV so the replay demo is self-contained
        sample_csv = tmp_path / "NVDA_1m.csv"
        with sample_csv.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["ts","symbol","price"])
            for k in range(60):
                w.writerow([f"2025-01-01T00:{k:02d}:00Z", "NVDA", 100.0 + k])

    session = "NVDA_REPLAY_TEST"
    summary_path = repo_root / f"replay_summary_NVDA_{session}.json"

    # Clean up any previous run
    if summary_path.exists():
        summary_path.unlink()

    cmd = [
        sys.executable,
        str(tools_dir / "run_bar_replay_to_json.py"),
        "--symbol",
        "NVDA",
        "--csv",
        str(sample_csv),
        "--session",
        session,
        "--outdir",
        str(repo_root),
    ]

    subprocess.run(cmd, check=True)

    assert summary_path.exists(), f"Expected replay summary at {summary_path}"
    data = json.loads(summary_path.read_text())
    assert data.get("symbol") == "NVDA"
    assert "ev" in data
    assert isinstance(data["ev"], dict)
