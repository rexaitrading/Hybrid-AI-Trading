param(
  [string]$HealthUrl     = "http://127.0.0.1:8787/health",
  [int]   $IBPortPrimary = 4002,
  [string]$IBGoodRoot    = "C:\Jts\ibgateway\1039\",
  [switch]$KillStrayIBG,
  [Nullable[int]]$IBUseSSL = $null,
  [switch]$StayOpen
)

$ErrorActionPreference = "Stop"
$fail = @()
function Add-Fail([string]$m){ $script:fail += $m }
function Step([string]$m){ Write-Host "[preflight] $m" }

Write-Host "[preflight] start pid=$PID PS=$($PSVersionTable.PSVersion)"

# 0) Env
try {
  Step "env: set PYTHONPATH"
  $env:PYTHONPATH = "$PWD\src;$env:PYTHONPATH"
} catch {
  Add-Fail "PYTHONPATH failed: $($_.Exception.Message)"
}

# 1) Provider health (WARN only)
try {
  Step "providers: health GET $HealthUrl"
  $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec 8 -Uri $HealthUrl
  if ($r.StatusCode -ne 200) {
    Write-Host "  WARN: Health HTTP $($r.StatusCode)"
  } else {
    Write-Host "  health: OK ($($r.StatusCode))"
  }
} catch {
  Write-Host "  WARN: Health fetch failed: $($_.Exception.Message)"
}

# 2) IBG cleanup (optional)
try {
  if ($KillStrayIBG) {
    Step "ibg: kill stray .bak/disabled"
    Get-CimInstance Win32_Process |
      Where-Object { $_.ExecutablePath -match 'ibgateway' -and $_.ExecutablePath -match '\.bak|disabled' } |
      ForEach-Object { try { Stop-Process -Id $_.ProcessId -Force -EA Stop } catch {} }
  }
} catch {
  Add-Fail "KillStrayIBG failed: $($_.Exception.Message)"
}

# 3) IB port + owner (WARN owner if not readable)
try {
  Step "ibg: probe port $IBPortPrimary"
  $lis = Get-NetTCPConnection -State Listen -LocalPort $IBPortPrimary -EA SilentlyContinue | Select-Object -First 1
  if (-not $lis) {
    Add-Fail "IB API not listening on $IBPortPrimary (Gateway Paper expected)"
  } else {
    $owner = $null
    try {
      $ci = Get-CimInstance Win32_Process -Filter ("ProcessId={0}" -f $lis.OwningProcess) -EA SilentlyContinue
      $owner = $ci.ExecutablePath
    } catch {}
    if (-not $owner) {
      try { $owner = (Get-Process -Id $lis.OwningProcess -EA SilentlyContinue).Path } catch {}
    }
    if ($owner) {
      Write-Host "  owner: $owner"
      if ($owner -notlike "$IBGoodRoot*") { Write-Host "  WARN: IBG owner path differs from expected root $IBGoodRoot" }
    } else {
      Write-Host "  WARN: Cannot read IBG owner ExecutablePath (run Admin for full detail)"
    }
  }
} catch {
  Add-Fail "IB probe failed: $($_.Exception.Message)"
}

# 4) Verdict
if ($fail.Count) {
  Write-Host "❌ PRE-FLIGHT: NO-GO"
  $fail | ForEach-Object { Write-Host " - $_" }
  if ($StayOpen) { [void](Read-Host "Press Enter to close") }
  exit 1
} else {
  Write-Host "✅ PRE-FLIGHT: GO"
  if ($StayOpen) { [void](Read-Host "Press Enter to close") }
  exit 0
}