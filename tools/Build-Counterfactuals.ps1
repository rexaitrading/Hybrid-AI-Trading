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

$barsDir = Join-Path $logsDirOut "bars"
$outPath = Join-Path $logsDirOut "counterfactuals.jsonl"

if(-not (Test-Path -LiteralPath $barsDir)){
  # Truth-preserving: write a blocked record (no fake counterfactuals)
  $obj = [ordered]@{
    schema = "counterfactual.v1"
    ts_utc = (Get-Date).ToUniversalTime().ToString("o")
    market = $mk
    symbol = $sy
    status = "blocked_missing_bars"
    reason = ("missing bars dir: " + $barsDir)
  }
  Write-Utf8NoBomLf $outPath (($obj | ConvertTo-Json -Compress -Depth 6) + "`n")
  Write-Host ("[OK] wrote " + $outPath + " status=blocked_missing_bars")
  exit 0
}

Fail "bars directory exists but counterfactual engine not yet implemented in this tool"
