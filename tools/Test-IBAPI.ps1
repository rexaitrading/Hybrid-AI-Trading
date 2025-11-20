[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# 1) Locate Python in local venv
$py = ".venv\\Scripts\\python.exe"
if (-not (Test-Path $py)) {
    throw "Python venv not found at $py"
}

# 2) Python snippet: run sanity_probe and emit a single PROBE_JSON line
$code = @"
import sys, json

# Ensure C:\Dev\HybridAITrading\src is on sys.path
sys.path.insert(0, r'C:\\Dev\\HybridAITrading\\src')

from hybrid_ai_trading.utils.preflight import sanity_probe

def main():
    # Fixed probe for now: AAPL, 1 share, allow_ext=True, no force_when_closed
    probe = sanity_probe(symbol='AAPL', qty=1, cushion=0.10, allow_ext=True, force_when_closed=False)
    # Emit single tagged line so PowerShell can parse it reliably
    print('PROBE_JSON:' + json.dumps(probe, default=str))

if __name__ == '__main__':
    main()
"@

# 3) Run Python and capture all output (stdout + stderr), but do NOT stop on errors
$oldEAP = $ErrorActionPreference
$ErrorActionPreference = "Continue"
try {
    $raw = & $py -c $code 2>&1
} finally {
    $ErrorActionPreference = $oldEAP
}

if (-not $raw) {
    Write-Host "IB API: FAIL (no output from sanity_probe)" -ForegroundColor Red
    return
}

# 4) Find the PROBE_JSON line
$probeLine = $raw | Where-Object { $_ -like 'PROBE_JSON:*' } | Select-Object -Last 1

if (-not $probeLine) {
    Write-Host "IB API: FAIL (sanity_probe did not emit PROBE_JSON; raw output below)" -ForegroundColor Red
    $raw | ForEach-Object { Write-Host "  $_" }
    return
}

$prefix = 'PROBE_JSON:'
$idx = $probeLine.IndexOf($prefix)
if ($idx -lt 0) {
    Write-Host "IB API: FAIL (could not parse PROBE_JSON line)" -ForegroundColor Red
    return
}

$jsonText = $probeLine.Substring($prefix.Length)

# 5) Parse JSON into a PowerShell object
try {
    $probe = $jsonText | ConvertFrom-Json
} catch {
    Write-Host "IB API: FAIL (JSON parse error from sanity_probe)" -ForegroundColor Red
    Write-Host "Raw JSON:" -ForegroundColor Yellow
    Write-Host $jsonText
    return
}

# 6) Extract session info and status
$session = $probe.session
$nowEt   = $session.now_et
$sessTag = $session.session
$okTime  = [bool]$session.ok_time

$status  = if ($probe.ok -and $okTime) { "OK" } elseif ($probe.ok) { "OK" } else { "FAIL" }

if ($status -eq "FAIL") {
    $reason = $probe.reason
    if (-not $reason) { $reason = "unknown" }
    Write-Host ("IB API: FAIL (reason={0}, session={1}, now_et={2})" -f $reason, $sessTag, $nowEt) -ForegroundColor Red
    return
}

# If we reach here, sanity_probe.ok is True
Write-Host ("IB API: OK (session={0}, ok_time={1}, now_et={2})" -f $sessTag, $okTime, $nowEt) -ForegroundColor Green