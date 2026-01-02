[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)]
  [string]$Message,

  [Parameter(Mandatory=$false)]
  [string[]]$Paths = @(),

  [Parameter(Mandatory=$false)]
  [switch]$All,

  [Parameter(Mandatory=$false)]
  [string[]]$Pytest = @(),

  [Parameter(Mandatory=$false)]
  [switch]$Push,

  [Parameter(Mandatory=$false)]
  [switch]$AllowDirty,

  [Parameter(Mandatory=$false)]
  [switch]$NoVerify
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null

function Fail([string]$msg){
  Write-Host "[GIT-SAFE] FAIL: $msg" -ForegroundColor Red
  exit 2
}
function Info([string]$msg){ Write-Host "[GIT-SAFE] $msg" -ForegroundColor Cyan }
function Warn([string]$msg){ Write-Host "[GIT-SAFE] WARN: $msg" -ForegroundColor Yellow }

if(-not (Test-Path -LiteralPath ".\.git")){
  Fail "Not in repo root (.git missing). cd to repo root and retry."
}

$msg = ("" + $Message).Trim()
if([string]::IsNullOrWhiteSpace($msg)){
  Fail "Commit message is empty."
}

Info "git status --porcelain"
git status --porcelain | Out-Host

Info "git diff --stat"
git diff --stat | Out-Host

if(-not $AllowDirty){
  $dirty = (git status --porcelain | Measure-Object).Count
  if($dirty -gt 0 -and (-not $All) -and ($Paths.Count -eq 0)){
    Fail "Working tree has changes. Provide -Paths, or use -All, or explicitly -AllowDirty."
  }
}

if($All){
  Info "Staging ALL changes"
  git add -A | Out-Host
} elseif($Paths.Count -gt 0){
  Info ("Staging paths: " + ($Paths -join ", "))
  git add -- @Paths | Out-Host
} else {
  Warn "No -Paths and no -All. Not staging anything automatically."
}

Info "git status --porcelain (after stage)"
git status --porcelain | Out-Host

if($Pytest.Count -gt 0){
  $py = ".\.venv\Scripts\python.exe"
  if(-not (Test-Path -LiteralPath $py)){
    Fail "Python venv missing at $py (cannot run pytest)."
  }
  Info ("Running pytest targets: " + ($Pytest -join " "))

  $env:PYTHONNOUSERSITE="1"
  $env:PYTHONDONTWRITEBYTECODE="1"
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH = (Join-Path (Get-Location) "src")

  & $py -m pytest -q @Pytest
  $rc = $LASTEXITCODE
  Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
  if($rc -ne 0){ Fail "pytest failed rc=$rc" }
}

$nv = @()
if($NoVerify){ $nv = @("--no-verify") }

Info "Committing"
git commit -m $msg @nv | Out-Host
if($LASTEXITCODE -ne 0){ Fail "git commit failed rc=$LASTEXITCODE" }

if($Push){
  Info "Pushing"
  git push | Out-Host
  if($LASTEXITCODE -ne 0){ Fail "git push failed rc=$LASTEXITCODE" }
}

Info "OK"
exit 0
