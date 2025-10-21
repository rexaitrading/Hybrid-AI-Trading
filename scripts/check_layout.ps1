$ErrorActionPreference='Stop'; Set-StrictMode -Version Latest
function Write-Section([string]$t){ $bar=('='*78); Write-Host "`n$bar`n# $t`n$bar" }
function Out-Both([string]$s){ $null=$script:BUF.AppendLine($s); Write-Host $s }

$BUF = New-Object System.Text.StringBuilder
$root = (Get-Location).Path
$src  = Join-Path $root 'src\hybrid_ai_trading'
$report = Join-Path $root "__layout_audit.txt"

Write-Section "Roots"
Out-Both ("root = {0}" -f $root)
Out-Both ("src  = {0}" -f $src)

Write-Section "Stray Python outside src/hybrid_ai_trading (excluding tests/scripts/.venv)"
$exclude = '\\\.venv\\|\\tests\\|\\scripts\\|\\research-env\\|\\__pycache__\\|\\logs\\'
$pyOutside = Get-ChildItem -Recurse -File -Include *.py |
  Where-Object { $_.FullName -notmatch [regex]::Escape($src) -and $_.FullName -notmatch $exclude }
if($pyOutside){ 
  $pyOutside | Select-Object FullName,Length,LastWriteTime | Format-Table -Auto | Out-String | % { Out-Both $_ }
}else{ Out-Both "(none)" }

Write-Section "Backup/temporary sources (*.bak*|*~|.#*|.orig)"
$bak = Get-ChildItem -Recurse -File -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -match '\.bak|\.orig$|~$|^\.\#' }
if($bak){ 
  $bak | Select-Object FullName,LastWriteTime,Length | Format-Table -Auto | Out-String | % { Out-Both $_ }
}else{ Out-Both "(none)" }

Write-Section "Packages missing __init__.py under src/hybrid_ai_trading"
$dirs = Get-ChildItem -Recurse -Directory -Path $src | Where-Object { $_.FullName -notmatch '\\__pycache__\\' }
$missingInit = @()
foreach($d in $dirs){
  $init = Join-Path $d.FullName '__init__.py'
  if(-not (Test-Path $init)){ $missingInit += $d.FullName }
}
if($missingInit){ $missingInit | % { Out-Both $_ } } else { Out-Both "(none)" }

Write-Section "Duplicate module filenames (root vs src) that could shadow"
$rootPy = Get-ChildItem -File -Include *.py -Path $root
if($rootPy){
  $rootNames = $rootPy | Select-Object -ExpandProperty Name
  $dupes = foreach($n in $rootNames){ Get-ChildItem -Recurse -File -Path $src -Filter $n }
  if($dupes){ $dupes | Select-Object Name,FullName | Format-Table -Auto | Out-String | % { Out-Both $_ } }
  else { Out-Both "(none)" }
}else{ Out-Both "(none at repo root)" }

Write-Section "Empty packages (dirs with only __pycache__ or nothing)"
$empty = foreach($d in $dirs){
  $files = Get-ChildItem -File -Path $d.FullName -ErrorAction SilentlyContinue | Where-Object { $_.Name -ne '__init__.py' }
  $subdirs = Get-ChildItem -Directory -Path $d.FullName -ErrorAction SilentlyContinue | Where-Object { $_.Name -ne '__pycache__' }
  if(-not $files -and -not $subdirs){ $d.FullName }
}
if($empty){ $empty | % { Out-Both $_ } } else { Out-Both "(none)" }

Write-Section "Untracked potentially-important files under src (git)"
try {
  $untracked = (& git ls-files --others --exclude-standard src) 2>$null
  if($untracked){ ($untracked -split "`r?`n") | ? { $_ } | % { Out-Both $_ } } else { Out-Both "(none)" }
}catch{ Out-Both "(git not available)" }

[IO.File]::WriteAllText($report, $BUF.ToString(), [Text.UTF8Encoding]::new($false))
Out-Both ("`nSaved report: {0}" -f $report)
