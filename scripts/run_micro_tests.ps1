param(
  [switch]$Install,
  [ValidateSet("Isolated","RespectIni")]
  [string]$Mode = "Isolated"
)
$ErrorActionPreference = "Stop"
Write-Host "RUNNER MODE: $Mode"

# UTF-8 & clean env
chcp 65001 > $null
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$env:PYTHONIOENCODING = "utf-8"; $env:PYTHONUTF8 = "1"; $env:PYTEST_ADDOPTS = ""

if ($Install) {
  python -m pip install --upgrade pip --disable-pip-version-check --no-color | Out-Null
  python -m pip install -U pytest        --disable-pip-version-check --no-color | Out-Null
}

$repo = Resolve-Path "."
$env:PYTHONPATH = (Join-Path $repo "src")
$t1 = (Resolve-Path "tests\test_marketable_limit.py").Path
$t2 = (Resolve-Path "tests\test_ib_safe_unit.py").Path

function Write-Utf8NoBom($p,$s){ [System.IO.File]::WriteAllText($p,$s,[System.Text.UTF8Encoding]::new($false)) }
function Test-PytestCovAvailable{ try{ (python -c "import importlib.util,sys; sys.stdout.write('ok' if importlib.util.find_spec('pytest_cov') else 'no')") -eq 'ok' }catch{ $false } }
function Strip-CovFromIni([string]$Src,[string]$Dst){
  $raw = Get-Content -Raw -Path $Src
  $lines = $raw -split "`r?`n"
  $out = foreach($line in $lines){
    if($line -match '^\s*addopts\s*='){
      $rest  = $line -replace '^\s*addopts\s*=\s*',''
      $parts = $rest -split '\s+'
      $kept  = @(); foreach($p in $parts){ if($p -and ($p -notmatch '^--cov')){ $kept += $p } }
      'addopts = ' + ($kept -join ' ')
    } else { $line }
  }
  Write-Utf8NoBom $Dst (($out -join "`n") + "`n")
}
function New-IsolatedRun([string]$T1,[string]$T2){
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
  $tmpDir = Join-Path $env:TEMP ("pytest_iso_{0}" -f ([Guid]::NewGuid()))
  New-Item -ItemType Directory -Path $tmpDir | Out-Null
  $tmpIni = Join-Path $tmpDir "pytest.ini"
  Write-Utf8NoBom $tmpIni "[pytest]`naddopts = -q --maxfail=1 --disable-warnings`ntestpaths = .`n"
  Push-Location $tmpDir
  try{ python -m pytest -c $tmpIni --rootdir $tmpDir --confcutdir $tmpDir -p no:pytest_cov $T1 $T2 }finally{
    Pop-Location; Remove-Item -Recurse -Force $tmpDir -ErrorAction SilentlyContinue
  }
}

if ($Mode -eq "RespectIni") {
  $iniPath = Join-Path $repo "pytest.ini"
  $hasIni  = Test-Path $iniPath
  $covInIni = $false; if ($hasIni) { $covInIni = Select-String -Path $iniPath -Pattern "--cov" -SimpleMatch -Quiet }
  if ($covInIni) {
    if ($Install) { python -m pip install -U pytest-cov --disable-pip-version-check --no-color | Out-Null }
    if (Test-PytestCovAvailable) {
      $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = $null
      python -m pytest -p pytest_cov --cov=hybrid_ai_trading.broker.ib_safe $t1 $t2
    } else {
      Write-Host "pytest-cov not available; stripping --cov* from repo pytest.ini and running without coverage." -ForegroundColor Yellow
      $tmpDir = Join-Path $env:TEMP ("pytest_respect_no_cov_{0}" -f ([Guid]::NewGuid()))
      New-Item -ItemType Directory -Path $tmpDir | Out-Null
      $tmpIni = Join-Path $tmpDir "pytest.ini"
      Strip-CovFromIni -Src $iniPath -Dst $tmpIni
      $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
      python -m pytest -c $tmpIni --rootdir $repo --confcutdir $repo -p no:pytest_cov $t1 $t2
      Remove-Item -Recurse -Force $tmpDir -ErrorAction SilentlyContinue
    }
  } else {
    $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
    python -m pytest -p no:pytest_cov $t1 $t2
  }
} else {
  New-IsolatedRun -T1 $t1 -T2 $t2
}
