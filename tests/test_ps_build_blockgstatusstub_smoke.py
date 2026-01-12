import subprocess
from pathlib import Path

REPO = Path(r"C:\HATJ\HybridAITrading")
POWERSHELL = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"

def _run_ps(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", *args],
        cwd=REPO,
        capture_output=True,
        text=True,
    )

def test_build_blockgstatusstub_parser_ok():
    # ParseFile smoke gate: catches "try inside hashtable", missing braces, etc.
    cmd = r"""
$fAbs=(Resolve-Path -LiteralPath ".\tools\Build-BlockGStatusStub.ps1").Path
$tokens=$null; $errs=$null
[System.Management.Automation.Language.Parser]::ParseFile($fAbs,[ref]$tokens,[ref]$errs) | Out-Null
if($errs){
  $errs | ForEach-Object { $_.Message } | Out-Host
  exit 2
}
exit 0
""".strip()
    cp = subprocess.run([POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd],
                        cwd=REPO, capture_output=True, text=True)
    assert cp.returncode == 0, f"Parser errors\\nSTDOUT:\\n{cp.stdout}\\nSTDERR:\\n{cp.stderr}"

def test_build_blockgstatusstub_strictmode_runs():
    # StrictMode smoke: ensures all referenced vars are defined (fail-closed).
    cp = _run_ps([r".\tools\Build-BlockGStatusStub.ps1", "-Symbol", "ALL", "-Market", "US"])
    assert cp.returncode == 0, f"rc={cp.returncode}\\nSTDOUT:\\n{cp.stdout}\\nSTDERR:\\n{cp.stderr}"
