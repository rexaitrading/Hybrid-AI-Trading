[CmdletBinding()]
param(
  [ValidateSet("NVDA")]
  [string]$Symbol = "NVDA",

  [switch]$Once,

  [int]$TimeoutSec = 240
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null

function Fail([string]$m){ throw ("[PAPERLIVE-OPS] FAIL-CLOSED: " + $m) }

# --- repo root (canonical, deterministic) ---
$repoRoot = & (Join-Path $PSScriptRoot "Go-RepoRoot.ps1")
if(-not $repoRoot){ Fail "Go-RepoRoot returned empty" }
$repoRoot = [System.IO.Path]::GetFullPath($repoRoot)
Set-Location -LiteralPath $repoRoot
[System.Environment]::CurrentDirectory = $repoRoot

Write-Host ("[PAPERLIVE-OPS] start Symbol=" + $Symbol) -ForegroundColor Cyan

# Load canonical secrets into THIS process (no args; canonical loader)
. (Join-Path $repoRoot "tools\Load-HatSecrets.ps1")

# Intel refresh (non-breaking)
powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Run-IntelNews.ps1") *>&1 | Out-Host
if($LASTEXITCODE -ne 0){ Fail ("Run-IntelNews failed exit=" + $LASTEXITCODE) }

powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Run-IntelYouTube.ps1") *>&1 | Out-Host
if($LASTEXITCODE -ne 0){ Fail ("Run-IntelYouTube failed exit=" + $LASTEXITCODE) }

# NVDA paper ops pipeline (stream->events->summaries->evhard->blockg)
$pOps = Join-Path $repoRoot "tools\Run-NvdaPaperOps.ps1"
if(-not (Test-Path -LiteralPath $pOps)){ Fail "Missing required tool: tools\Run-NvdaPaperOps.ps1" }

if($Once){
  Write-Host ("[PAPERLIVE-OPS] Once=true => Run-NvdaPaperOps timeout_sec=" + $TimeoutSec) -ForegroundColor Yellow
$tmpDir = "C:\Trading\tmp"; if(-not (Test-Path -LiteralPath $tmpDir)){ New-Item -ItemType Directory -Force -Path $tmpDir | Out-Null }
$stdout = Join-Path $tmpDir "paperops_stdout.txt"
$stderr = Join-Path $tmpDir "paperops_stderr.txt"
  try { Remove-Item -LiteralPath $stdout,$stderr -Force -ErrorAction SilentlyContinue } catch {}

  $psExe = (Get-Command powershell).Source
  $p = Start-Process -FilePath $psExe -ArgumentList @("-NoProfile","-ExecutionPolicy","Bypass","-File",$pOps) -PassThru -NoNewWindow `
        -RedirectStandardOutput $stdout -RedirectStandardError $stderr

$ok = $p.WaitForExit([int]($TimeoutSec * 1000))
  if(-not $ok){
    try { Stop-Process -Id $p.Id -Force } catch {}
    Write-Host "[PAPERLIVE-OPS] FAIL-CLOSED: Run-NvdaPaperOps timed out" -ForegroundColor Red
    if(Test-Path -LiteralPath $stdout){ Get-Content -LiteralPath $stdout -Tail 80 -Encoding UTF8 | Out-Host }
    if(Test-Path -LiteralPath $stderr){ Get-Content -LiteralPath $stderr -Tail 120 -Encoding UTF8 | Out-Host }
    exit 2
  }

  $rc = [int]$p.ExitCode
  if(Test-Path -LiteralPath $stdout){ Get-Content -LiteralPath $stdout -Tail 120 -Encoding UTF8 | Out-Host }
  if(Test-Path -LiteralPath $stderr){ Get-Content -LiteralPath $stderr -Tail 120 -Encoding UTF8 | Out-Host }

  if($rc -ne 0){
    Write-Host ("[PAPERLIVE-OPS] FAIL-CLOSED: Run-NvdaPaperOps exit=" + $rc) -ForegroundColor Red
    exit 2
  }

  if(-not (Test-Path -LiteralPath (Join-Path $repoRoot "logs\blockg_status_stub.json"))){
    Fail "Run-NvdaPaperOps finished but blockg_status_stub.json missing"
  }

Write-Host "[PAPERLIVE-OPS] Once=true => done (paper ops only). Exiting 0." -ForegroundColor Green
exit 0

} else {
  powershell -NoProfile -ExecutionPolicy Bypass -File $pOps *>&1 | Out-Host
  if($LASTEXITCODE -ne 0){ Fail ("Run-NvdaPaperOps failed exit=" + $LASTEXITCODE) }
}
# ContractPack rebuild + check
powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Run-Premarket-ContractPack.ps1") -Symbol $Symbol *>&1 | Out-Host
if($LASTEXITCODE -ne 0){ Fail ("Run-Premarket-ContractPack failed exit=" + $LASTEXITCODE) }

powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Check-BlockGReady.ps1") -Symbol $Symbol *>&1 | Out-Host
Write-Host ("[PAPERLIVE-OPS] EXIT_BLOCKG=" + $LASTEXITCODE) -ForegroundColor Yellow

exit $LASTEXITCODE