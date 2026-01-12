import json
from pathlib import Path
import subprocess
import os

def test_check_blockgready_denies_when_crisis_regime_true(tmp_path):
    # Take an existing stub as template
    src = Path("logs/US/blockg_status_stub.json")
    assert src.exists(), "run Build-BlockGStatusStub -Market US first"
    data = json.loads(src.read_text(encoding="utf-8"))

    # Force crisis
    data["crisis_ok_today"] = True
    data["crisis_regime"] = True

    # Write temp stub + point contract to it
    p = tmp_path / "blockg_status_stub.json"
    p.write_text(json.dumps(data), encoding="utf-8")

    env = os.environ.copy()
    env["HAT_BLOCKG_STATUS_PATH"] = str(p)

    ps = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
    cp = subprocess.run([ps,"-NoProfile","-ExecutionPolicy","Bypass","-File","tools/Check-BlockGReady.ps1","-Market","US","-Mode","SYMBOL_ONLY","-Symbol","NVDA"], env=env, capture_output=True, text=True)

    assert cp.returncode == 2
    assert "crisis_regime=true" in (cp.stdout + cp.stderr)
