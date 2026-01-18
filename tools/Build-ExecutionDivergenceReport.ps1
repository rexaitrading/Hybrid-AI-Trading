[CmdletBinding()]
param(
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","HK_SH","HK_SZ")]
  [string]$Market = "US",

  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol = "NVDA",

  [ValidateSet("PAPER","PAPERLIVE","LIVE")]
  [string]$Mode = "PAPERLIVE"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

function Fail([string]$m){ throw ("[FAIL-CLOSED] " + $m) }

function Write-Utf8NoBomLf([string]$Path,[string]$Text){
  $t = ($Text -replace "`r`n","`n" -replace "`r","`n")
  if($t.Length -eq 0 -or $t[-1] -ne "`n"){ $t += "`n" }
  [System.IO.File]::WriteAllText($Path, $t, (New-Object System.Text.UTF8Encoding($false)))
}

# Repo root
$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
try { $repoRoot = (Resolve-Path -LiteralPath $repoRoot -ErrorAction Stop).Path } catch {}
Set-Location -LiteralPath $repoRoot
[System.Environment]::CurrentDirectory = $repoRoot

# Resolve RunContext (single truth)
$rcPath = Join-Path $toolsDir "Resolve-RunContext.ps1"
if(-not (Test-Path -LiteralPath $rcPath)){ Fail ("missing tool: " + $rcPath) }

$mk = ($Market + "").Trim().ToUpperInvariant()
$sy = ($Symbol + "").Trim().ToUpperInvariant()

$rcRaw = (& $rcPath -Market $mk -Symbol $sy 2>&1 | Out-String)
$r = ($rcRaw + "").Trim()
$i0 = $r.IndexOf('{'); $i1 = $r.LastIndexOf('}')
if($i0 -lt 0 -or $i1 -le $i0){ Fail ("Resolve-RunContext did not return JSON market=" + $mk) }
$rcObj = $null
try { $rcObj = ($r.Substring($i0, ($i1-$i0+1)) | ConvertFrom-Json -ErrorAction Stop) } catch { Fail "RunContext JSON parse failed" }

if(-not ($rcObj.PSObject.Properties.Name -contains "logs_dir_out")){ Fail "RunContext missing logs_dir_out" }
$logsDirOut = ([string]$rcObj.logs_dir_out).Trim()
if(-not $logsDirOut){ Fail "RunContext logs_dir_out empty" }

# Inputs (FAIL-CLOSED if missing)
$slipPath = Join-Path $logsDirOut "execution\slippage_events.jsonl"
$simPath  = Join-Path $logsDirOut "fill_sim_report.json"

if(-not (Test-Path -LiteralPath $slipPath)){ Fail ("missing slippage_events.jsonl: " + $slipPath) }
if(-not (Test-Path -LiteralPath $simPath)){ Fail ("missing fill_sim_report.json: " + $simPath) }

# Output
$outPath = Join-Path $logsDirOut "execution_divergence_report.json"

# Load sim report
$sim = Get-Content -LiteralPath $simPath -Raw -Encoding UTF8 | ConvertFrom-Json

# Load slippage events (last N)
$lines = @(Get-Content -LiteralPath $slipPath -Encoding UTF8 -ErrorAction Stop | Where-Object { ($_ + "").Trim() } | Select-Object -Last 200)
$events = @()
foreach($ln in $lines){
  try { $events += ($ln | ConvertFrom-Json -ErrorAction Stop) } catch { }
}
if($events.Count -eq 0){ Fail "no parsable slippage events" }

# Minimal divergence summary (no fake latency/partials unless present in sources)
$slips = @($events | ForEach-Object { [double]$_.slip_bps })
$max  = ($slips | Measure-Object -Maximum).Maximum
$avg  = ($slips | Measure-Object -Average).Average

$obj = [ordered]@{
  schema = "execution_divergence_report.v1"
  ts_utc = (Get-Date).ToUniversalTime().ToString("o")
  market = $mk
  symbol = $sy
  mode = $Mode
  logs_dir_out = $logsDirOut

  inputs = [ordered]@{
    slippage_events_jsonl = $slipPath
    fill_sim_report_json  = $simPath
  }

  sim_summary = $sim.summary
  slippage_bps = [ordered]@{
    samples = [int]$slips.Count
    avg     = [Math]::Round([double]$avg, 4)
    max     = [Math]::Round([double]$max, 4)
  }

  note = "MVP: joins simulator summary with observed slippage events. Latency/partials/spread require additional real-fill logs; this report is fail-closed on missing inputs."
}

Write-Utf8NoBomLf $outPath (($obj | ConvertTo-Json -Depth 10))
Write-Host ("[OK] wrote " + $outPath)