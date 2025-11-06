param([string]$Workflow='TradeEngine Dev Tests',[switch]$NoOpen)
$ErrorActionPreference='Stop'; New-Item -ItemType Directory -Force .reports | Out-Null
$runObj = gh run list --workflow "$Workflow" --limit 1 --json databaseId | ConvertFrom-Json
if(-not $runObj){ throw "No recent runs for '$Workflow'." }
$runId = $runObj[0].databaseId
$st = (gh run view $runId --json status | ConvertFrom-Json).status
if($st -in @('queued','in_progress')){ gh run watch $runId | Out-Host }

$prefix = ".\.reports\tradeengine_dev_tests"
$agg    = "$prefix`_$runId.log"
gh run view $runId --log | Out-File $agg -Encoding utf8

$jobsObj = (gh run view $runId --json jobs | ConvertFrom-Json).jobs
foreach($j in $jobsObj){ $jobId = if($j.id){$j.id}elseif($j.databaseId){$j.databaseId}else{$null}
  if($jobId){ $safe=($j.name -replace '[^\w\-]','_'); gh run view $runId --job $jobId --log | Out-File "$prefix`_job_${jobId}_$safe.log" -Enc utf8 } }

$sum  = [IO.Path]::ChangeExtension($agg,'summary.txt')
$reds = Get-Content $agg | Select-String -Pattern '=== short test summary info ===|^FAILED\s|^ERROR\s|Traceback|AssertionError|E\s{3,}|Process completed with exit code|Command failed with exit code|::error|pip ERR|ModuleNotFoundError|SyntaxError'
if($reds){ $reds | Set-Content $sum -Enc utf8 } else {
  @("CI summary for run $runId","----------------------------------------","No failures found. Job completed with success.",(Get-Content $agg | Select-String -Pattern 'completed with')) | Set-Content $sum -Enc utf8
}
if(-not $NoOpen){ notepad $sum }
