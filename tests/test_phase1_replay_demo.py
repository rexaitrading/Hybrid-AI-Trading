import json
import subprocess
import sys
from pathlib import Path


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

    assert sample_csv.exists(), f"Sample NVDA CSV not found at {sample_csv}"

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