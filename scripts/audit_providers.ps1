param(
  [string]$Repo   = (Get-Location).Path,
  [string]$SrcRel = "src",
  [string]$Py     = ".\.venv\Scripts\python.exe",
  [switch]$ApplyFixes,
  [switch]$Fix     # alias for ApplyFixes
)
if ($Fix) { $ApplyFixes = $true }

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Write-Section([string]$title) {
  $bar = ('=' * 70)
  "`n$bar`n# $title`n$bar"
}
function Use-UTF8NoBOM { [System.Text.UTF8Encoding]::new($false) }

function Invoke-PyInline {
  param(
    [Parameter(Mandatory)] [string] $Code,
    [string] $Python = $Py,
    [string] $RepoRoot = $Repo,
    [string] $SrcRelPath = $SrcRel
  )
  $tmp = [System.IO.Path]::ChangeExtension([System.IO.Path]::GetTempFileName(), ".py")
  [System.IO.File]::WriteAllText($tmp, $Code, (Use-UTF8NoBOM))
  try {
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $Python
    $psi.Arguments = "`"$tmp`""
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError  = $true
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $pp = (Join-Path $RepoRoot $SrcRelPath)
    $psi.EnvironmentVariables["PYTHONPATH"] = "$pp;$($env:PYTHONPATH)"
    $p = [System.Diagnostics.Process]::Start($psi)
    $stdout = $p.StandardOutput.ReadToEnd()
    $stderr = $p.StandardError.ReadToEnd()
    $p.WaitForExit()
    [pscustomobject]@{
      ExitCode = $p.ExitCode
      StdOut   = $stdout
      StdErr   = $stderr
      File     = $tmp
    }
  } finally {
    Remove-Item -LiteralPath $tmp -ErrorAction SilentlyContinue
  }
}

function Ensure-Dir([string]$path) {
  if (-not (Test-Path -LiteralPath $path)) {
    New-Item -ItemType Directory -Path $path -Force | Out-Null
  }
}

# ----- paths -----
$src = Join-Path $Repo $SrcRel
$scr = Join-Path $Repo "scripts"
$dataClients = Join-Path $src "hybrid_ai_trading\data_clients"
$utilsDir    = Join-Path $src "hybrid_ai_trading\utils"
$configDir   = Join-Path $Repo "config"

# Presence
$presence = @(
  (Join-Path $configDir 'providers.yaml')
  (Join-Path $utilsDir  'providers.py')
) | ForEach-Object {
  [pscustomobject]@{ Path = $_; Exists = Test-Path -LiteralPath $_ }
}

# ----- banner -----
Write-Section "Provider Audit — Start"
"Repo        : $Repo"
"Src         : $src"
"Scripts     : $scr"
"Python      : $Py"
"ApplyFixes  : $($ApplyFixes.IsPresent)"
""

# 1) Presence
Write-Section "Presence check"
$presence | Format-Table -Auto

# 2) Misplaced/suspicious
Write-Section "Search for misplaced providers or wrong extensions"

$misplaced = @()
$legacyProvDir = Join-Path $src "providers"
if (Test-Path $legacyProvDir) {
  $misplaced = @(
    Get-ChildItem -Path $legacyProvDir -Filter *.py -Recurse -ErrorAction SilentlyContinue |
    Select-Object FullName, Length, LastWriteTime
  )
}

$psl = @(
  Get-ChildItem -Path $Repo -Filter *.psl -Recurse -ErrorAction SilentlyContinue |
  Select-Object FullName, Length, LastWriteTime
)
$hostCollide = @()
if (Test-Path $scr) {
  $hostCollide = @(
    Get-ChildItem -Path $scr -Filter *.ps1 -Recurse -ErrorAction SilentlyContinue |
    ForEach-Object {
      $t = Get-Content -LiteralPath $_.FullName -Raw
      if ($t -match '(?m)^\s*\$Host\b') { $_.FullName }
    }
  )
}

if ((($misplaced | Measure-Object).Count) -gt 0) { "Misplaced provider python files (found under src\providers\):"; $misplaced | Format-Table -Auto } else { "No misplaced provider files under src\providers\." }
if ((($psl       | Measure-Object).Count) -gt 0) { "Found .psl files (should be .ps1):";               $psl | Format-Table -Auto } else { "No .psl files found." }
if ((($hostCollide | Measure-Object).Count) -gt 0) { 'Scripts using $Host variable (rename to $ApiHost or similar):'; $hostCollide | Format-Table -Auto } else { "No `\$Host collisions found in scripts." }

# Fixes
if ($ApplyFixes) {
  Write-Section "ApplyFixes: migrating providers, renaming .psl, patching `$Host"
  if ((($misplaced | Measure-Object).Count) -gt 0) {
    Ensure-Dir $dataClients
    foreach ($f in $misplaced) {
      $srcPath = $f.FullName
      $name = [System.IO.Path]::GetFileName($srcPath)
      if ($name -match '^provider_(.+)\.py$') { $stem = $Matches[1]; $dest = Join-Path $dataClients ("{0}_client.py" -f $stem) }
      else { $base = [System.IO.Path]::GetFileNameWithoutExtension($name); $dest = Join-Path $dataClients ("{0}_client.py" -f $base) }
      if (Test-Path -LiteralPath $dest) { Write-Warning "Destination already exists, skipping: $dest" } else { Move-Item -LiteralPath $srcPath -Destination $dest; "Moved: $srcPath -> $dest" }
    }
    try {
      $left = Get-ChildItem -Path $legacyProvDir -Recurse -Force -ErrorAction SilentlyContinue
      if (-not $left -or $left.Count -eq 0) { Remove-Item -LiteralPath $legacyProvDir -Force -Recurse -ErrorAction SilentlyContinue; "Removed empty legacy dir: $legacyProvDir" }
    } catch { }
  } else { "No legacy provider files to move." }

  if ((($psl | Measure-Object).Count) -gt 0) {
    foreach ($p in $psl) {
      $newPath = [System.IO.Path]::ChangeExtension($p.FullName, ".ps1")
      if (Test-Path -LiteralPath $newPath) { Write-Warning "Target exists, skipping rename: $newPath" } else { Rename-Item -LiteralPath $p.FullName -NewName $newPath; "Renamed: $($p.FullName) -> $newPath" }
    }
  } else { "No .psl files to rename." }

  if ((($hostCollide | Measure-Object).Count) -gt 0) {
    foreach ($file in $hostCollide) {
      $txt = Get-Content -LiteralPath $file -Raw
      $patched = [regex]::Replace($txt, '(?m)(?<![\w\$])\$Host(?![\w])', '$ApiHost')
      if ($patched -ne $txt) { 'Patched $Host -> $ApiHost in: ' + $file; [IO.File]::WriteAllText($file, $patched, (Use-UTF8NoBOM)) } else { "No change needed in: $file" }
    }
  } else { "No `$Host collisions to patch." }
}

# 3) Python import smoke
Write-Section "Python import smoke (data_clients)"
$imports = @(
  "from hybrid_ai_trading.data_clients.polygon_client import Client as P; print('polygon_client:OK')",
  "from hybrid_ai_trading.data_clients.coinapi_client import Client as C; print('coinapi_client:OK')",
  "from hybrid_ai_trading.data_clients.benzinga_client import Client as B; print('benzinga_client:OK')"
)
foreach ($code in $imports) {
  $res = Invoke-PyInline -Code $code -RepoRoot $Repo -SrcRelPath $SrcRel
  $tag = ($code -split '\s+')[1]
  if ($res.ExitCode -eq 0) { "OK: $tag" } else { "FAIL: $tag"; if ($res.StdErr) { "  STDERR: " + ($res.StdErr.Trim() -replace '\s+',' ') } }
}

# 4) Load providers.yaml
Write-Section "Load providers.yaml via your loader"
$pyLoad = @"
from hybrid_ai_trading.utils.providers import load_providers
import json
cfg = load_providers('config/providers.yaml')
print(json.dumps(cfg, indent=2)[:1000])
"@
$resLoad = Invoke-PyInline -Code $pyLoad -RepoRoot $Repo -SrcRelPath $SrcRel
if ($resLoad.ExitCode -eq 0) { "providers.yaml loaded OK (first 1KB):"; $resLoad.StdOut.Trim() } else { "providers.yaml failed to load. Check YAML format and env placeholders."; if ($resLoad.StdErr) { "STDERR: " + $resLoad.StdErr.Trim() } }

# 5) get_price smoke
Write-Section "get_price/get_price_retry smoke"
$pyTest = @"
from hybrid_ai_trading.utils.providers import load_providers, get_price, get_price_retry
cfg = load_providers('config/providers.yaml')
print(get_price('AAPL', cfg))
print(get_price_retry('AAPL', cfg, attempts=3, delay=0.4))
"@
$resPrice = Invoke-PyInline -Code $pyTest -RepoRoot $Repo -SrcRelPath $SrcRel
if ($resPrice.ExitCode -eq 0) { "get_price output:"; $resPrice.StdOut.Trim() } else { "get_price failed. Likely missing API keys or HTTP blocked."; if ($resPrice.StdErr) { "STDERR: " + $resPrice.StdErr.Trim() } }

# 6) Summary (hardened)
Write-Section "Summary & recommendations"

$missing = @(
  $presence | Where-Object { -not $_.Exists } | Select-Object -ExpandProperty Path
)
if ((($missing | Measure-Object).Count) -gt 0) { "Missing key files:"; $missing | ForEach-Object { " - $_" } } else { "All expected key files present." }
if ((($misplaced   | Measure-Object).Count) -gt 0) { ">> Detected provider files under src\providers\. Move them to src\hybrid_ai_trading\data_clients and rename to *_client.py"; "   Example: src\providers\provider_polygon.py -> src\hybrid_ai_trading\data_clients\polygon_client.py" }
if ((($psl         | Measure-Object).Count) -gt 0) { ">> Rename .psl to .ps1: use Rename-Item, e.g. Rename-Item scripts\foo.psl foo.ps1" }
if ((($hostCollide | Measure-Object).Count) -gt 0) { '>> Replace $Host variable with $ApiHost (or similar) in listed scripts to avoid PS collisions.' }

""
"Provider sanity:"
$adv = @()
$provJson = $resLoad.StdOut
if ($provJson -match '<your-polygon-key>') { $adv += ' - polygon key is placeholder; set a real key or disable polygon.' }
if ($provJson -match '<your-coinapi-key>')  { $adv += ' - coinapi key is placeholder; set a real key or disable coinapi.' }
if ($provJson -match '"benzinga"\s*:\s*{[^}]*"key"[^}]*}' -and $provJson -notmatch '"benzinga"[^}]*"base"') { $adv += ' - benzinga missing "base"; your client likely requires both key+base.' }
if ((($adv | Measure-Object).Count) -gt 0) { $adv } else { " - no obvious provider config issues detected." }

"`n==================================================================="
"Audit complete."
