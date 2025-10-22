param(
  [string]$Config   = "config/paper_runner.yaml",
  [string]$Universe = "AAPL,MSFT",
  [int]   $MDT      = 3,
  [switch]$EnforceRiskHub = $true,
  [switch]$SnapshotsWhenClosed = $true,
  [string]$LogFile  = "logs/runner_paper.jsonl",
  [string]$JobName  = "PaperLoop"
)
$ErrorActionPreference = 'Stop'
$env:PYTHONPATH = "$PWD\src;$env:PYTHONPATH"
New-Item -ItemType Directory -Force -Path (Split-Path $LogFile) | Out-Null

# Stop any existing job with same name (safe)
Get-Job -Name $JobName -ErrorAction SilentlyContinue | Stop-Job -PassThru -ErrorAction SilentlyContinue | Remove-Job -Force -ErrorAction SilentlyContinue

$args = @("--config", $Config, "--universe", $Universe, "--mdt", $MDT, "--log-file", $LogFile)
if ($EnforceRiskHub) { $args += "--enforce-riskhub" }
if ($SnapshotsWhenClosed) { $args += "--snapshots-when-closed" }

$script = {
  param($py, $runner, $args)
  & $py -u $runner @args
}
$job = Start-Job -Name $JobName -ScriptBlock $script -ArgumentList ".\.venv\Scripts\python.exe","scripts\run_paper_with_risk.py",$args
"Started job: $($job.Id)  Name=$($job.Name)"
Get-Job -Name $JobName | Format-List Id,Name,State,HasMoreData
