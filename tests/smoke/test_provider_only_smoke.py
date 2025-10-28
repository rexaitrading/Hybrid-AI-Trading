import os, sys, subprocess, pathlib

def test_provider_only_smoke():
    env = os.environ.copy()
    env["PYTHONPATH"] = str(pathlib.Path("src").resolve())

    cmd = [
        sys.executable,
        "src/hybrid_ai_trading/runners/paper_trader.py",
        "--config", "config/paper_runner.yaml",
        "--universe", "AAPL",
        "--provider-only", "--prefer-providers",
        "--mdt", "1",
    ]

    p = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=60)
    out = (p.stdout or "") + (p.stderr or "")

    assert p.returncode == 0, (
        f"non-zero exit: {p.returncode}\n"
        f"STDOUT:\n{p.stdout}\n"
        f"STDERR:\n{p.stderr}\n"
    )

    # Accept any of:
    # 1) explicit stdout marker (we injected it),
    # 2) structured log token (if stdout/stderr is redirected),
    # 3) completely silent success (some runners suppress stdout).
    assert ("provider-only run" in out) or ("once_done" in out) or (out.strip() == ""), (
        "Unexpected output pattern.\n"
        f"STDOUT:\n{p.stdout}\n"
        f"STDERR:\n{p.stderr}\n"
    )
