import subprocess
from pathlib import Path

REPO = Path(r"C:\HATJ\HybridAITrading")
POWERSHELL = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"

def _run_ps_file(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", *args],
        cwd=REPO,
        capture_output=True,
        text=True,
    )

def test_check_blockgready_parser_ok():
    cmd = r"""
$fAbs=(Resolve-Path -LiteralPath ".\tools\Check-BlockGReady.ps1").Path
$tokens=$null; $errs=$null
[System.Management.Automation.Language.Parser]::ParseFile($fAbs,[ref]$tokens,[ref]$errs) | Out-Null
if($errs){
  $errs | ForEach-Object { $_.Message } | Out-Host
  exit 2
}
exit 0
""".strip()
    cp = subprocess.run(
        [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, f"Parser errors\nSTDOUT:\n{cp.stdout}\nSTDERR:\n{cp.stderr}"

def test_check_blockgready_build_only_ok():
    cp = _run_ps_file([r".\tools\Check-BlockGReady.ps1", "-Symbol", "NVDA", "-Market", "US", "-Mode", "BUILD_ONLY"])
    assert cp.returncode == 0, f"rc={cp.returncode}\nSTDOUT:\n{cp.stdout}\nSTDERR:\n{cp.stderr}"

def test_check_blockgready_all_strict_session_gate_message():
    # We only assert the session gate message when the market is open-day but not RTH.
    cp = _run_ps_file([r".\tools\Check-BlockGReady.ps1", "-Symbol", "NVDA", "-Market", "US", "-Mode", "ALL_STRICT"])
    if "market_session_not_rth" in (cp.stdout + cp.stderr):
        assert cp.returncode == 2
