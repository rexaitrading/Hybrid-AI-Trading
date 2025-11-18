# tests/test_replay_wrapper_json.py
import json, subprocess, sys, pathlib, os

ROOT = pathlib.Path(__file__).resolve().parents[1]
PY   = sys.executable
WRAP = ROOT / "scripts" / "replay_cli.py"
CSV  = os.environ.get("REPLAY_CSV", r"C:\Data\minute\AAPL_2025-10-01.csv")

def test_wrapper_emits_json_line():
    assert WRAP.exists(), "scripts/replay_cli.py missing"
    p = subprocess.run(
        [PY, str(WRAP),
         "--csv", CSV, "--symbol", "T",
         "--mode", "fast", "--speed", "10",
         "--fees-per-share", "0.0", "--slippage-ps", "0.0",
         "--orb-minutes", "5", "--risk-cents", "20", "--max-qty", "200",
         "--force-exit", "--summary", "json"],
        capture_output=True, text=True, check=True
    )
    line = p.stdout.strip().splitlines()[-1]
    obj = json.loads(line)
    # shape & types
    for k in ["symbol","bars","trades","pnl","final_qty","fees_ps","slippage_ps"]:
        assert k in obj
    assert isinstance(obj["bars"], int)
    assert isinstance(obj["trades"], int)
    assert isinstance(obj["pnl"], (int, float))
