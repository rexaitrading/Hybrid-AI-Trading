[CmdletBinding(DefaultParameterSetName="Commit")]
param(
  # Commit message (MANDATORY). Prevents "typed message becomes a command".
  [Parameter(Mandatory=$true, ParameterSetName="Commit")]
  [Parameter(Mandatory=$true, ParameterSetName="DryRun")]
  [string]$Message,

  # Optional list of paths to stage (Commit mode only).
  [Parameter(Mandatory=$false, ParameterSetName="Commit")]
  [string[]]$Paths = @(),

  # Stage all changes (Commit mode only; use consciously).
  [Parameter(Mandatory=$false, ParameterSetName="Commit")]
  [switch]$All,

  # Optional pytest targets to run before commit (Commit mode only).
  [Parameter(Mandatory=$false, ParameterSetName="Commit")]
  [string[]]$Pytest = @(),

  # If set, pushes after commit (Commit mode only).
  [Parameter(Mandatory=$false, ParameterSetName="Commit")]
  [switch]$Push,

  # Allow commit even if working tree has other unstaged changes (Commit mode only; default fail-closed).
  [Parameter(Mandatory=$false, ParameterSetName="Commit")]
  [switch]$AllowDirty,

  # If set, bypass git hooks (Commit mode only).
  [Parameter(Mandatory=$false, ParameterSetName="Commit")]
  [switch]$NoVerify,

  # Print actions only; do NOT stage/commit/push. (DryRun mode only)
  [Parameter(Mandatory=$true, ParameterSetName="DryRun")]
  [switch]$DryRun
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

# --- Repo root guard ---
if(-not (Test-Path -LiteralPath ".\.git")){
  Fail "Not in repo root (.git missing). cd to repo root and retry."
}

# --- Message guard ---
$msg = ("" + $Message).Trim()
if([string]::IsNullOrWhiteSpace($msg)){
  Fail "Commit message is empty."
}

# --- Always show status & diff summary ---
Info "git status --porcelain"
git status --porcelain | Out-Host

Info "git diff --stat"
git diff --stat | Out-Host

# --- DryRun: PRINT ONLY (no stage/commit/push) ---
if($PSCmdlet.ParameterSetName -eq "DryRun"){
  Warn "DryRun enabled: printing intended actions only (no stage/commit/push)."
  if($All){ Warn "NOTE: -All is not allowed in DryRun parameter set (should not happen)." }
  if($Paths.Count -gt 0){ Warn "NOTE: -Paths is not allowed in DryRun parameter set (should not happen)." }
  if($Push){ Warn "NOTE: -Push is not allowed in DryRun parameter set (should not happen)." }
  Info ("Would commit message: " + $msg)
  exit 0
}

# --- Dirty guard (fail-closed unless AllowDirty) ---
if(-not $AllowDirty){
  $dirty = (git status --porcelain | Measure-Object).Count
  if($dirty -gt 0 -and (-not $All) -and ($Paths.Count -eq 0)){
    Fail "Working tree has changes. Provide -Paths, or use -All, or explicitly -AllowDirty."
  }
}

# --- Stage changes ---
if($All){
  Info "Staging ALL changes"
  git add -A | Out-Host
} elseif($Paths.Count -gt 0){
  Info ("Staging paths: " + ($Paths -join ", "))
  git add -- $Paths | Out-Host
} else {
  Warn "No -Paths and no -All. Not staging anything automatically."
}

# --- Post-stage summary ---
Info "git status --porcelain (after stage)"
git status --porcelain | Out-Host

# --- Guard: refuse to commit if nothing is staged (fail-closed) ---
$staged = (git diff --cached --name-only | Measure-Object).Count
if($staged -le 0){
  Fail "Nothing staged. Provide -Paths or -All to stage changes before commit."
}

# --- Optional tests (fail-closed) ---
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

# --- Commit ---
$nv = @()
if($NoVerify){ $nv = @("--no-verify") }

Info "Committing"
git commit -m $msg @nv | Out-Host
if($LASTEXITCODE -ne 0){ Fail "git commit failed rc=$LASTEXITCODE" }

# --- Push (optional) ---
if($Push){
  Info "Pushing"
  git push | Out-Host
  if($LASTEXITCODE -ne 0){ Fail "git push failed rc=$LASTEXITCODE" }
}

Info "OK"
exit 0
