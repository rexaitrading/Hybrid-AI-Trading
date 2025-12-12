import json
import os
import subprocess
import sys
from pathlib import Path


def test_nvda_replay_demo_creates_summary_with_stats(tmp_path, monkeypatch):
    """
    Phase-1: NVDA bar replay → EV summary JSON smoke test.

    - Uses existing data/nvda_1min_sample.csv
    - Calls tools/run_bar_replay_to_json.py
    - Asserts replay_summary_NVDA_<session>.json is created and has EV stats.
    """
    repo_root = Path(__file__).resolve().parents[1]
    tools_dir = repo_root / "tools"
    data_dir  = repo_root / "data"
    sample_csv = data_dir / "nvda_1min_sample.csv"

    assert sample_csv.exists(), f"Sample NVDA CSV not found at {sample_csv}"

    session = "NVDA_REPLAY_TEST"
    summary_path = repo_root / f"replay_summary_NVDA_{session}.json"

    # Clean up any previous run
    if summary_path.exists():
        summary_path.unlink()

    cmd = [
        sys.executable,
        str(tools_dir / "run_bar_replay_to_json.py"),
        "--symbol", "NVDA",
        "--csv", str(sample_csv),
        "--session", session,
        "--outdir", str(repo_root),
    ]

    env = os.environ.copy()
    result = subprocess.run(cmd, cwd=repo_root, env=env, capture_output=True, text=True)
    assert result.returncode == 0, f"Replay script failed: {result.stderr}"

    assert summary_path.exists(), f"Summary JSON not created at {summary_path}"

    data = json.loads(summary_path.read_text())

    # Basic structure
    assert data["symbol"] == "NVDA"
    assert data["session"] == session
    assert "bars" in data
    assert isinstance(data["bars"], int)

    # EV block
    assert "ev" in data
    assert "mean" in data["ev"]
    assert "stdev" in data["ev"]

    # Richer stats presence (values may be 0.0 for stub data)
    for key in ["mean_edge_ratio", "max_drawdown_pct", "win_rate", "avg_win", "avg_loss"]:
        assert key in data
