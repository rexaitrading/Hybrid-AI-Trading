[CmdletBinding()]
param(
  [string]$AsOfDate = ""
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Set-Location $repoRoot

$today = if ([string]::IsNullOrWhiteSpace($AsOfDate)) { (Get-Date).ToString("yyyy-MM-dd") } else { $AsOfDate }

$src = Join-Path $repoRoot "logs\nvda_phase5_paperlive_results.jsonl"
if (-not (Test-Path $src)) { throw "Missing: $src" }

$py = Join-Path $repoRoot ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "Missing python: $py" }

$script = @"
import json, sys
from hybrid_ai_trading.risk.risk_phase5_ev_bands import get_ev_and_band

today = sys.argv[1]
src = sys.argv[2]

out_lines = []
miss_before = 0
miss_after = 0
today_rows = 0

with open(src, "r", encoding="utf-8-sig") as f:
    for line in f:
        ln = line.strip()
        if not ln:
            continue
        try:
            o = json.loads(ln)
        except Exception:
            continue

        ts = o.get("ts_trade") or ""
        if isinstance(ts, str) and len(ts) >= 10 and ts[:10] == today:
            today_rows += 1
            if o.get("ev_mu") is None:
                miss_before += 1

            if o.get("ev_mu") is None or o.get("ev_band_abs") is None:
                ev, band = get_ev_and_band(str(o.get("regime") or "NVDA_BPLUS_LIVE"))
                o.setdefault("ev_mu", ev)
                o.setdefault("ev_band_abs", band)
                p5 = o.get("phase5_result") or {}
                p5.setdefault("ev_mu", o.get("ev_mu"))
                p5.setdefault("ev_band_abs", o.get("ev_band_abs"))
                p5.setdefault("source", "ev_band_table")
                o["phase5_result"] = p5

            if o.get("ev_mu") is None:
                miss_after += 1

        out_lines.append(json.dumps(o, separators=(",", ":"), ensure_ascii=False))

tmp = src + ".tmp"
with open(tmp, "w", encoding="utf-8", newline="\n") as w:
    for ln in out_lines:
        w.write(ln + "\n")

print(f"[EV-BACKFILL] today={today} today_rows={today_rows} miss_before={miss_before} miss_after={miss_after}")
"@

$scriptPath = Join-Path $repoRoot "tools\_tmp_backfill_evmu.py"
$utf8 = New-Object System.Text.UTF8Encoding($false)
[IO.File]::WriteAllText($scriptPath, ($script -replace "`r`n","`n") + "`n", $utf8)

$out = & $py $scriptPath $today $src
Write-Host $out

Move-Item -Force ($src + ".tmp") $src
Remove-Item -Force $scriptPath
