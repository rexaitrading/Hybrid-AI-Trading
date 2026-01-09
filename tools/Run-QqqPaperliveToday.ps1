[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

# --- OUTPUT ENCODING (institutional) ---
try {
  $utf8 = New-Object System.Text.UTF8Encoding($false)
  [Console]::OutputEncoding = $utf8
  [Console]::InputEncoding  = $utf8
  $global:OutputEncoding    = $utf8
} catch { }
# --- END OUTPUT ENCODING ---

function Fail([string]$m){
  Write-Host ("[QQQ-TODAY] FAIL-CLOSED: " + $m) -ForegroundColor Red
  exit 2
}

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Set-Location -LiteralPath $repoRoot

$py = Join-Path $repoRoot ".venv\Scripts\python.exe"
if(-not (Test-Path -LiteralPath $py)){ Fail "missing python venv: $py" }

$outPath = Join-Path $repoRoot "logs\\paper_trader_qqq_today.jsonl"
New-Item -ItemType Directory -Force -Path (Split-Path $outPath -Parent) | Out-Null

& $py -c "from hybrid_ai_trading.runners.paper_trader import cli_run_once_safe; raise SystemExit(cli_run_once_safe('QQQ', r'logs/paper_trader_qqq_today.jsonl', provider_only=True))" *>&1 | Out-Host
if($LASTEXITCODE -ne 0){ Fail "python cli_run_once_safe exit=$LASTEXITCODE" }

if(-not (Test-Path -LiteralPath $outPath)){ Fail "missing output file: $outPath" }

$tail = Get-Content -LiteralPath $outPath -Tail 600 -Encoding utf8
$txt = ($tail -join "`n")
if($txt -match 'stub_engine' -or $txt -match 'with_micro_stub_engine_v1'){
  Fail "stub markers detected in output => $outPath"
}

Write-Host ("[QQQ-TODAY] OK: wrote " + $outPath) -ForegroundColor Green
exit 0