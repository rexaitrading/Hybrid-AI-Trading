param(
  [Parameter(Mandatory=$true)]
  [string]$Title,

  [string]$Why = "",
  [string]$Files = "",

  [string]$Tests = "powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Pytest-Chokepoint.ps1 -q",
  [switch]$SkipTests,

  # Authority-file patch override (default: FAIL-CLOSED)
  [switch]$ForceProtected
)
$ErrorActionPreference='Stop'
# --- [PATCH-GUARD] FAIL-CLOSED PATCH GUARD (authority files) ---
# Default: refuse patching core authority files unless explicitly allowed.
# Override: pass -ForceProtected OR set env HAT_ALLOW_PATCH_GUARD=1

$guardAllow = ($ForceProtected -or ($env:HAT_ALLOW_PATCH_GUARD -eq "1"))

# Self-parse sanity (prevents recursion-corruption)
try {
  $null = [System.Management.Automation.Language.Parser]::ParseFile($PSCommandPath, [ref]$null, [ref]$null)
} catch {
  Write-Error "[PATCH-GUARD] FAIL-CLOSED: log_patch.ps1 does not parse. Refusing to run."
  exit 2
}

# Authority files (relative paths)
$authorityRel = @(
  "tools\Build-BlockGStatusStub.ps1",
  "tools\Check-BlockGReady.ps1",
  "tools\pytest.ps1",
  "tools\Pytest-Chokepoint.ps1",
  "tools\Run-WeekdayPreMarketLock.ps1",
  "tools\Run-DailyOps-OneTap.ps1"
)

$repoRoot_guard = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$authorityFull = @()
foreach($r in $authorityRel){
  $p = Join-Path $repoRoot_guard $r
  if(Test-Path -LiteralPath $p){ $authorityFull += (Resolve-Path -LiteralPath $p).Path }
}

function _IsProtectedTarget([string]$candidate){
  if(-not $candidate){ return $false }
  try {
    $full = (Resolve-Path -LiteralPath $candidate -ErrorAction Stop).Path
    foreach($a in $authorityFull){ if($full -ieq $a){ return $true } }
  } catch { }
  return $false
}

if(-not $guardAllow){
  foreach($tok in ($Files -split '[,; ]+' | Where-Object { $_ })){
    if(_IsProtectedTarget $tok){
[Console]::Error.WriteLine("[PATCH-GUARD] FAIL-CLOSED: refusing protected target in -Files: " + $tok + " (set HAT_ALLOW_PATCH_GUARD=1 or pass -ForceProtected)")
exit 2
      exit 2
    }
  }
}
# --- [PATCH-GUARD] END ---

$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$logDir = Join-Path (Resolve-Path ".\logs") $stamp
New-Item -ItemType Directory -Force $logDir | Out-Null


New-Item -ItemType Directory -Force ".\.backup" | Out-Null
# Backups
$filesList = ($Files -split '[,; ]+') | ? { $_ -and (Test-Path $_) }
foreach($f in $filesList){ Copy-Item $f ".\.backup\$(Split-Path $f -Leaf).$stamp.bak" -Force }

# Git diffs if repo
$inGit = $false; try{ git rev-parse --is-inside-work-tree *> $null; $inGit=$true }catch{}
if($inGit){ git diff > (Join-Path $logDir "pre.diff") }

# Tests
if(-not $SkipTests){
  $out = Join-Path $logDir "tests.out.txt"
  try{ $env:PYTEST_ADDOPTS="--maxfail=1"; Write-Host ">> $Tests" -ForegroundColor Cyan; Invoke-Expression $Tests | Tee-Object -FilePath $out }
  catch{ $_ | Out-File -FilePath $out -Append }
}

# Post diff
if($inGit){ git diff > (Join-Path $logDir "post.diff") }

# PATCHLOG entry
$patchlog = ".\docs\PATCHLOG.md"
if(-not (Test-Path $patchlog)){ "# PATCHLOG (surgical changes)`n" | Out-File -FilePath $patchlog -Encoding utf8 }
$tail = ""; $testsOut = Join-Path $logDir "tests.out.txt"; if(Test-Path $testsOut){ $tail = (Get-Content $testsOut -Tail 20) -join "`n" }
$entry = @"
## $stamp  $Title
**Why:** $Why

**Files:** $Files
**Logs:** ./logs/$stamp/
**Backups:** ./.backup/*.$stamp.bak

**Tests:** $Tests

**Summary (tail):**
$tail

---
"@
Add-Content -Path $patchlog -Value $entry -Encoding utf8
Write-Host ("Logged patch  {0}" -f $patchlog) -ForegroundColor Green
Write-Host ("Logs dir      {0}" -f $logDir)   -ForegroundColor Green
