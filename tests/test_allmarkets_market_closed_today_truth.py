import json
import subprocess
from datetime import date

REPO = r"C:\HATJ\HybridAITrading"

def _run_ps(args: list[str]) -> str:
    cp = subprocess.run(
        [r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", *args],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    if cp.returncode != 0:
        raise RuntimeError(f"pwsh failed rc={cp.returncode}\nSTDOUT:\n{cp.stdout}\nSTDERR:\n{cp.stderr}")
    return cp.stdout

def _json_from_ps(args: list[str]) -> dict:
    out = _run_ps(args).strip()
    # Resolve-MarketContext returns JSON on stdout
    return json.loads(out)

def _market_log_root(mkt: str) -> str:
    out = _run_ps([r".\tools\Get-MarketLogRoot.ps1", "-Market", mkt]).strip()
    return out if out else (REPO + r"\logs")

def test_allmarkets_market_closed_today_truth():
    as_of = date.today().isoformat()
    for mkt in ["US", "JP", "HK", "SG"]:
        mc = _json_from_ps([r".\tools\Resolve-MarketContext.ps1", "-Market", mkt, "-AsOfDate", as_of])
        # Build stub for that market (writes into market log root)
        _run_ps([r".\tools\Build-BlockGStatusStub.ps1", "-Symbol", "ALL", "-Market", mkt])

        lr = _market_log_root(mkt)
        stub_path = lr + r"\blockg_status_stub.json"
        with open(stub_path, "r", encoding="utf-8") as f:
            st = json.load(f)

        assert bool(st.get("market_closed_today")) == bool(mc.get("market_closed_today")), (mkt, st.get("market_closed_today"), mc.get("market_closed_today"))
