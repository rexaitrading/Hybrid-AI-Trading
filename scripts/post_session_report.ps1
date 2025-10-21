$ErrorActionPreference='Stop'
New-Item -ItemType Directory -Force -Path .\.logs\session_reports | Out-Null
$report = Join-Path .\.logs\session_reports ("report_{0}.txt" -f (Get-Date -Format 'yyyy-MM-dd'))

$healthPath = ".\.logs\provider_health.log"
$health = if (Test-Path $healthPath) { Get-Content $healthPath -Tail 200 } else { @() }

$ok  = @($health | Select-String -SimpleMatch ' ok=').Count
$bad = @($health | Select-String -SimpleMatch ' BAD').Count

$lines = @(
  "Report: $(Get-Date -Format 'yyyy-MM-dd')"
  "Provider checks (tail 200): $ok OK / $bad BAD"
  "PnL(realized): N/A (wire from runner logs)"
  "Slippage(avg): N/A (wire from runner logs)"
)
Set-Content -Encoding UTF8 -LiteralPath $report -Value $lines
"Created: $report"
