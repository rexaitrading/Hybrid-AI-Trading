param(
  [Parameter(Mandatory=$true)][string]$Title,
  [string]$Why="", [string]$Files="", [string]$Tests="python -m pytest -q", [switch]$SkipTests
)
$ErrorActionPreference='Stop'
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$logDir = Join-Path (Resolve-Path ".\logs") $stamp
New-Item -ItemType Directory -Force $logDir | Out-Null

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
