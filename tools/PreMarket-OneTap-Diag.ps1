param(
  [switch]$CiMode,
  [switch]$SkipPorts = $false
)

if (-not (Get-Variable -Name SkipPorts -Scope Local -ErrorAction SilentlyContinue)) { $SkipPorts = $false }

$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$ProgressPreference = 'SilentlyContinue'

# --- paths ---
$utf8     = New-Object System.Text.UTF8Encoding($false)
$RepoRoot = (Get-Location).Path
$OneTap   = Join-Path $RepoRoot 'tools\PreMarket-OneTap.ps1'
$logDir   = 'C:\ProgramData'
if (-not (Test-Path $logDir)) { New-Item -Type Directory -Path $logDir -Force | Out-Null }
$DiagLog  = "C:\ProgramData\OneTap_Diag_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
$JsonOut  = "C:\ProgramData\OneTap_Diag_Result.json"

if (-not (Test-Path $OneTap)) { throw "Not found: $OneTap" }

# --- normalize OneTap to UTF-8 no-BOM + LF ---
$raw = Get-Content -Raw -Encoding Byte $OneTap
if ($raw.Length -ge 3 -and $raw[0] -eq 0xEF -and $raw[1] -eq 0xBB -and $raw[2] -eq 0xBF) {
  $raw = $raw[3..($raw.Length-1)]
  [IO.File]::WriteAllBytes($OneTap, $raw)
}
$txt = [System.Text.Encoding]::UTF8.GetString($raw) -replace "`r`n","`n"
[IO.File]::WriteAllText($OneTap, $txt, $utf8)

# --- helpers ---
function Write-Step([string]$name,[string]$status,[string]$msg='') {
  $line = '{0} | {1,-14} | {2}' -f (Get-Date -Format 'HH:mm:ss'), $name, ("$status $msg").Trim()
  Add-Content -Path $DiagLog -Value $line -Encoding UTF8
  Write-Host $line
}
function Wait-PortBound([int]$Port,[int]$TimeoutSec=10){
  $t0 = Get-Date
  while ((New-TimeSpan -Start $t0 -End (Get-Date)).TotalSeconds -lt $TimeoutSec) {
    $hit = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($hit) { return $true }
    Start-Sleep -Milliseconds 300
  }
  return $false
}

$steps  = @()
$failed = @()

try {
  # 1) Presence
  $steps += 'Presence'
  Write-Step 'Presence' 'RUN'
  $null = Get-Command powershell.exe
  if (-not (Test-Path $OneTap)) { throw 'OneTap missing' }
  Write-Step 'Presence' 'OK'

  # 2) Ports (smart, brief)
  $steps += 'Ports'
  Write-Step 'Ports' 'RUN'
  $hbPaper = Test-Path 'C:\IBC\ibg_status.json'
  $hbLive  = Test-Path 'C:\IBC\ibg_live_status.json'
  if ($SkipPorts -or ($hbPaper -and $hbLive)) {
    Write-Step 'Ports' ("SKIP (SkipPorts=$SkipPorts HBpaper=$hbPaper HBlive=$hbLive)")
  } else {
    $p4002 = Wait-PortBound -Port 4002
    $p4001 = Wait-PortBound -Port 4001
    Write-Step 'Ports' ("OK 4002=$p4002 4001=$p4001")
  }

  # 3) OneTap run in child host
  $steps += 'OneTap'
  Write-Step 'OneTap' 'RUN'
  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName  = 'powershell.exe'
  $psi.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$OneTap`""
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError  = $true
  $psi.UseShellExecute        = $false
  $proc = [System.Diagnostics.Process]::Start($psi)
  $stdOut = $proc.StandardOutput.ReadToEnd()
  $stdErr = $proc.StandardError.ReadToEnd()
  $proc.WaitForExit()
  $rc = $proc.ExitCode
  Add-Content -Path $DiagLog -Value ($stdOut + "`n" + $stdErr) -Encoding UTF8
  if ($rc -ne 0) { Write-Step 'OneTap' "FAIL rc=$rc"; $failed += "OneTap(rc=$rc)" } else { Write-Step 'OneTap' 'OK' }

  # 4) Heartbeats
  $steps += 'Sanity'
  Write-Step 'Sanity' 'RUN'
  foreach($hb in @('C:\IBC\ibg_status.json','C:\IBC\ibg_live_status.json')) {
    if (Test-Path $hb) { Write-Step 'Sanity' "HB:$([IO.Path]::GetFileName($hb)) OK" }
    else { Write-Step 'Sanity' "HB:$([IO.Path]::GetFileName($hb)) MISS"; $failed += "HB:$hb" }
  }
  Write-Step 'Sanity' 'OK'
}
catch {
  $failed += "EXC:$($_.Exception.Message)"
  Write-Step 'EXC' 'FAIL' $_.Exception.Message
}

# --- compute rc first (PS 5.1-safe) ---
$rc = if ($failed.Count -gt 0) { 1 } else { 0 }

# --- summarize ---
$result = [ordered]@{
  when    = (Get-Date).ToString('s')
  steps   = $steps
  failed  = $failed
  log     = $DiagLog
  rc      = $rc
}
($result | ConvertTo-Json -Depth 6) | Set-Content -Path $JsonOut -Encoding UTF8
"== DIAG JSON => $JsonOut"
"== LOG PATH  => $DiagLog"

# --- exit behavior: only close host in CI mode ---
if ($CiMode) { exit $rc }
