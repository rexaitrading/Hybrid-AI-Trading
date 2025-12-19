import os
import subprocess
import sys


def test_daily_build_cli_runs_and_returns_0_or_2():
    env = dict(os.environ)
    env["PYTHONNOUSERSITE"] = "1"
    env["PYTHONPATH"] = r"C:\HAT\src"

    cmd = [sys.executable, "-m", "hybrid_ai_trading.gatescore.daily_build", "--symbol", "NVDA"]
    p = subprocess.run(cmd, capture_output=True, text=True, env=env)
    assert p.returncode in (0, 2), p.stderr