[CmdletBinding()]
param(
  [Parameter(Mandatory=$false)]
  [string]$AsOfDate = "",

  [Parameter(Mandatory=$false)]
  [string]$InputPath = "logs\paper_trades.jsonl",

  [Parameter(Mandatory=$false)]
  [string]$OutputPath = "logs\paper_trades.jsonl"
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Set-Location $repoRoot

$today = if ([string]::IsNullOrWhiteSpace($AsOfDate)) { (Get-Date).ToString("yyyy-MM-dd") } else { $AsOfDate }

$in  = Join-Path $repoRoot $InputPath
$out = Join-Path $repoRoot $OutputPath


# Normalize in-place safety: always write to temp then replace
$tmp = $out + ".tmp_normalize_" + (Get-Date).ToString("yyyyMMdd_HHmmss")
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($tmp, "", $utf8NoBom)
if (-not (Test-Path $in)) { throw "Missing input: $in" }

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($tmp, "", $utf8NoBom)

$rowsIn = 0
$rowsOut = 0

Get-Content $in -Encoding utf8 | ForEach-Object {
  $ln = $_.Trim()
  if (-not $ln) { return }
  $rowsIn++
  try { $o = $ln | ConvertFrom-Json -ErrorAction Stop } catch { return }

  # Normalize common timestamp fields if present
  foreach ($k in @("ts","ts_trade","entry_ts","time","timestamp")) {
    try {
      if ($o.PSObject.Properties.Name -contains $k) {
        $v = "$($o.$k)"
        if ($v.Length -ge 19) { $o.$k = $today + $v.Substring(10) }
        elseif ($v.Length -ge 10) { $o.$k = $today + "T09:30:00" }
      }
    } catch { }
  }

  ($o | ConvertTo-Json -Compress) | Add-Content -Path $tmp -Encoding utf8
  $rowsOut++
}

# Replace output atomically
Move-Item -Force -LiteralPath $tmp -Destination $out

Write-Host ("[PAPER-TRADES] Normalized: in_rows={0} out_rows={1} as_of={2} out={3}" -f $rowsIn,$rowsOut,$today,$out) -ForegroundColor Green
exit 0