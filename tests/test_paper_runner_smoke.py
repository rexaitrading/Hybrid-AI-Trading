import json
import os
import subprocess
import sys


def run(args):
    p = subprocess.run(
        [sys.executable, "-m", "hybrid_ai_trading.runners.paper_runner", *args],
        capture_output=True,
        text=True,
        env=dict(os.environ, PYTHONPATH=os.path.join(os.getcwd(), "src")),
    )
    assert p.returncode == 0, p.stderr
    return p.stdout


def test_provider_only_once():
    out = run(
        [
            "--provider-only",
            "--dry-drill",
            "--once",
            "--universe",
            "AAPL,MSFT",
            "--mdt",
            "1",
        ]
    )
    first_line = next(
        l for l in out.splitlines() if l.startswith("[PaperRunner] args:")
    )
    payload = json.loads(first_line.split("args: ", 1)[1])
    assert payload["universe"] == ["AAPL", "MSFT"]
    assert payload["provider_only"] is True
    assert payload["once"] is True
