import os
import subprocess
import sys


def test_daily_build_cli_runs_and_returns_0_or_2(tmp_path):
    env = dict(os.environ)
    env["PYTHONNOUSERSITE"] = "1"
    env["PYTHONPATH"] = r"C:\HAT\src"

    out_path = tmp_path / "gs.jsonl"
    # status-path can point to the repo default; command must still return {0,2} and never crash
    cmd = [
        sys.executable,
        "-m",
        "hybrid_ai_trading.gatescore.daily_build",
        "--symbol",
        "NVDA",
        "--status-path",
        r"logs\blockg_status_stub.json",
        "--out",
        str(out_path),
    ]
    p = subprocess.run(cmd, capture_output=True, text=True, env=env)
    assert p.returncode in (0, 2), p.stderr