[CmdletBinding()]
param(
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","HK_SH","HK_SZ")]
  [string]$Market = "US",
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol = "NVDA"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

function Fail([string]$m){ throw ("[FAIL-CLOSED] " + $m) }
function Write-Utf8NoBomLf([string]$Path,[string]$Text){
  $t = ($Text -replace "`r`n","`n" -replace "`r","`n")
  if($t.Length -eq 0 -or $t[-1] -ne "`n"){ $t += "`n" }
  [System.IO.File]::WriteAllText($Path, $t, (New-Object System.Text.UTF8Encoding($false)))
}
function Read-JsonLines([string]$Path){
  $out=@()
  if(-not (Test-Path -LiteralPath $Path)){ return $out }
  foreach($ln in Get-Content -LiteralPath $Path -Encoding UTF8){
    $s = ($ln + "").Trim()
    if(-not $s){ continue }
    try { $out += ($s | ConvertFrom-Json -ErrorAction Stop) } catch {}
  }
  return $out
}

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
try { $repoRoot = (Resolve-Path -LiteralPath $repoRoot -ErrorAction Stop).Path } catch {}
Set-Location -LiteralPath $repoRoot
[System.Environment]::CurrentDirectory = $repoRoot

$rcPath = Join-Path $toolsDir "Resolve-RunContext.ps1"
if(-not (Test-Path -LiteralPath $rcPath)){ Fail ("missing tool: " + $rcPath) }

$mk = ($Market + "").Trim().ToUpperInvariant()
$sy = ($Symbol + "").Trim().ToUpperInvariant()

$rcRaw = (& $rcPath -Market $mk -Symbol $sy 2>&1 | Out-String).Trim()
$i0 = $rcRaw.IndexOf('{'); $i1 = $rcRaw.LastIndexOf('}')
if($i0 -lt 0 -or $i1 -le $i0){ Fail ("Resolve-RunContext did not return JSON market=" + $mk) }
$rcObj = ($rcRaw.Substring($i0, ($i1-$i0+1)) | ConvertFrom-Json -ErrorAction Stop)

$logsDirOut = ([string]$rcObj.logs_dir_out).Trim()
if(-not $logsDirOut){ Fail "RunContext logs_dir_out empty" }

$labelsPath = Join-Path $logsDirOut "trade_labels.jsonl"
if(-not (Test-Path -LiteralPath $labelsPath)){ Fail ("missing trade_labels.jsonl: " + $labelsPath) }

$labels = Read-JsonLines $labelsPath
if($labels.Count -eq 0){ Fail "trade_labels.jsonl empty" }

# Compute simple aggregates
$eq = @()
$xq = @()
foreach($r in $labels){
  try { if($null -ne $r.entry_quality){ $eq += [double]$r.entry_quality } } catch {}
  try { if($null -ne $r.exit_quality){ $xq += [double]$r.exit_quality } } catch {}
}

$avgEq = if($eq.Count -gt 0){ [Math]::Round((($eq | Measure-Object -Average).Average), 4) } else { $null }
$avgXq = if($xq.Count -gt 0){ [Math]::Round((($xq | Measure-Object -Average).Average), 4) } else { $null }

$day = ""
try { $day = ($labels[0].as_of_date + "") } catch { $day = "" }

$improvement = "Create bars cache for counterfactual engine (logs\US\bars missing)."

$md = @"
# Daily AAR — $mk / $sy — $day

## Summary
- Trades labeled: $($labels.Count)
- Avg entry quality: $avgEq
- Avg exit quality: $avgXq

## Tomorrow’s one improvement
- $improvement

## Notes (truth-preserving)
- Counterfactual engine blocked until bars cache exists under logs\<MKT>\bars.
- This AAR is generated from trade_labels.jsonl only (no guessing).
"@

$out = Join-Path $logsDirOut "daily_aar.md"
Write-Utf8NoBomLf $out $md
Write-Host ("[OK] wrote " + $out)
