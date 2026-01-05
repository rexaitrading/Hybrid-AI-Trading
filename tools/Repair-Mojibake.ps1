[CmdletBinding()]
param(
  [AllowEmptyCollection()]
  [string[]]$Paths = @(),

  [int]$MaxPasses = 8,

  [switch]$NormalizeLf
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# PS5.1 rule: ASCII-only source. No non-ASCII in code or comments.
# We build mojibake markers from code points at runtime.

$M_C3    = [string][char]0x00C3
$M_C2    = [string][char]0x00C2
$M_E2    = [string][char]0x00E2
$M_BOMTX = ([string][char]0x00EF) + ([string][char]0x00BB) + ([string][char]0x00BF)

$markers = @($M_C3, $M_C2, $M_E2, $M_BOMTX)

function HasMojibake([string]$s){
  foreach($m in $markers){
    if($s -like ("*" + $m + "*")){ return $true }
  }
  return $false
}

function FixOnce([string]$s){
  $latin1 = [System.Text.Encoding]::GetEncoding(28591)  # ISO-8859-1
  $utf8   = [System.Text.Encoding]::UTF8
  $bytes  = $latin1.GetBytes($s)
  return $utf8.GetString($bytes)
}

function WriteUtf8NoBom([string]$path, [string]$text){
  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($path, $text, $utf8NoBom)
}

$changed = 0
$checked = 0

foreach($p in $Paths){
  $checked++
  if(-not (Test-Path -LiteralPath $p)){
    Write-Warning ("SKIP missing: " + $p)
    continue
  }

  $full = (Resolve-Path -LiteralPath $p).Path
  $text = [System.IO.File]::ReadAllText($full, [System.Text.Encoding]::UTF8)
  $orig = $text
  $pass = 0

  while($pass -lt $MaxPasses -and (HasMojibake $text)){
    $text = FixOnce $text
    $pass++
  }

  if($NormalizeLf){
    $text = $text -replace "`r`n","`n"
    $text = $text -replace "`r","`n"
  }

  if($text -ne $orig){
    $backup = "$full.bak_mojibakefix_$(Get-Date -Format yyyyMMdd_HHmmss)"
    Copy-Item -LiteralPath $full -Destination $backup -Force
    WriteUtf8NoBom $full $text
    $changed++
    Write-Host ("FIXED (passes=" + $pass + "): " + $full)
  } else {
    Write-Host ("NOCHANGE: " + $full)
  }
}

Write-Host ("DONE checked=" + $checked + " changed=" + $changed)