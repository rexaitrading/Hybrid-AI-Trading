[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "ALL",

  [ValidateSet("US","JP","HK","SG","IN","KR","TW")]
  [string]$Market = "US"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

function Write-Utf8NoBomLf([string]$Path,[string]$Text){
  $utf8 = New-Object System.Text.UTF8Encoding($false)
  $Text = $Text -replace "`r`n","`n"
  if($Text.Length -gt 0 -and $Text[-1] -ne "`n"){ $Text += "`n" }
  [System.IO.File]::WriteAllText($Path,$Text,$utf8)
}

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = (Resolve-Path -LiteralPath (Split-Path -Parent $toolsDir)).Path
Set-Location -LiteralPath $repoRoot
[System.Environment]::CurrentDirectory = $repoRoot
$env:HAT_REPO_ROOT = $repoRoot

# Per-market logs root (same convention as BlockG)
$logsDirOut = $null
try {
  $logsDirOut = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Get-MarketLogRoot.ps1") -Market $Market
} catch { $logsDirOut = $null }
if(-not $logsDirOut){ $logsDirOut = Join-Path $repoRoot "logs" }
New-Item -ItemType Directory -Force -Path $logsDirOut | Out-Null

$py = Join-Path $repoRoot ".\.venv\Scripts\python.exe"
if(-not (Test-Path -LiteralPath $py)){ throw "Missing venv python: $py" }

$nowUtc = (Get-Date).ToUniversalTime()
$outPath = Join-Path $logsDirOut "crashmode_flatten_status.json"

# Capture full stdout/stderr without polluting JSON
$stdoutPath = Join-Path $logsDirOut "crashmode_flatten_last_stdout.txt"
$stderrPath = Join-Path $logsDirOut "crashmode_flatten_last_stderr.txt"
try { Remove-Item -LiteralPath $stdoutPath,$stderrPath -Force -ErrorAction SilentlyContinue } catch {}

$rc = 2
try {
  $p = Start-Process -FilePath $py -ArgumentList @(
      "-m","hybrid_ai_trading.runners.crashmode_flatten",
      "--market",$Market,
      "--symbol",$Symbol
    ) -NoNewWindow -Wait -PassThru -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
  $rc = [int]$p.ExitCode
} catch {
  $rc = 2
  try { $_.Exception.ToString() | Out-File -LiteralPath $stderrPath -Encoding UTF8 } catch {}
}

$payload = [ordered]@{
  ts_utc = $nowUtc.ToString("o")
  market = $Market
  symbol = $Symbol
  ok = ($rc -eq 0)
  exit_code = [int]$rc
  note = "CrashMode flatten tool (risk-action). Does not grant LIVE readiness."
}
Write-Utf8NoBomLf $outPath ($payload | ConvertTo-Json -Depth 6)

# Print captured output for operator visibility
if(Test-Path -LiteralPath $stdoutPath){ Get-Content -LiteralPath $stdoutPath -Encoding UTF8 -ErrorAction SilentlyContinue | Out-Host }
if(Test-Path -LiteralPath $stderrPath){ Get-Content -LiteralPath $stderrPath -Encoding UTF8 -ErrorAction SilentlyContinue | Out-Host }

if($rc -ne 0){ exit $rc }
Write-Host ("[FLATTEN] OK wrote " + $outPath) -ForegroundColor Green
exit 0
