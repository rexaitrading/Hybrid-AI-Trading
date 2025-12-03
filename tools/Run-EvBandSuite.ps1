param(
    [string]$PythonExe = ".\.venv\Scripts\python.exe"
)

$ErrorActionPreference = "Stop"
Write-Host "`n[EV-SUITE] Run EV-band + soft-veto suite" -ForegroundColor Cyan

# Ensure we run from repo root
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $repoRoot.EndsWith("tools")) {
    $repoRoot = Get-Location
} else {
    $repoRoot = Split-Path -Parent $repoRoot
}
Set-Location $repoRoot

# 1) Apply EV-bands to JSONL logs
Write-Host "`n[EV-SUITE] 1/4 Apply EV-bands to JSONL logs" -ForegroundColor Cyan
& $PythonExe tools\ev_band_apply_to_log.py --input "logs/nvda_phase5_paperlive_results.jsonl" --output "logs/nvda_phase5_paperlive_with_ev_band.jsonl" --default-regime "NVDA_BPLUS_LIVE"
& $PythonExe tools\ev_band_apply_to_log.py --input "logs/spy_phase5_paperlive_results.jsonl"  --output "logs/spy_phase5_paperlive_with_ev_band.jsonl"  --default-regime "SPY_ORB_LIVE"
& $PythonExe tools\ev_band_apply_to_log.py --input "logs/qqq_phase5_paperlive_results.jsonl"  --output "logs/qqq_phase5_paperlive_with_ev_band.jsonl"  --default-regime "QQQ_ORB_LIVE"

# 2) JSONL -> CSV (with soft_ev_*)
Write-Host "`n[EV-SUITE] 2/4 Rebuild EV-band CSVs (with soft_ev_veto/soft_ev_reason)" -ForegroundColor Cyan
& $PythonExe tools\ev_band_jsonl_to_csv.py --input "logs/nvda_phase5_paperlive_with_ev_band.jsonl" --output "logs/nvda_phase5_paperlive_with_ev_band.csv"
& $PythonExe tools\ev_band_jsonl_to_csv.py --input "logs/spy_phase5_paperlive_with_ev_band.jsonl"  --output "logs/spy_phase5_paperlive_with_ev_band.csv"
& $PythonExe tools\ev_band_jsonl_to_csv.py --input "logs/qqq_phase5_paperlive_with_ev_band.jsonl"  --output "logs/qqq_phase5_paperlive_with_ev_band.csv"

# 3) EV-band summary (band_A / band_B / below_min / missing)
Write-Host "`n[EV-SUITE] 3/4 EV-band reason counts" -ForegroundColor Cyan
& $PythonExe tools\ev_band_summary.py

# 4) band_below_min PnL report
Write-Host "`n[EV-SUITE] 4/4 band_below_min PnL report" -ForegroundColor Cyan
& $PythonExe tools\ev_band_below_min_report.py

# 5) Soft veto vs allow summary (bonus)
Write-Host "`n[EV-SUITE] Soft EV veto vs allow summary" -ForegroundColor Cyan
& $PythonExe tools\ev_soft_veto_demo.py

Write-Host "`n[EV-SUITE] DONE." -ForegroundColor Green