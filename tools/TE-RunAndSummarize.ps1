param([int]$Pr=26,[string]$WorkflowName='TradeEngine Dev Tests')
$ErrorActionPreference='Stop'; New-Item -ItemType Directory -Force .reports | Out-Null
$wfId = (gh workflow list | Select-String "$WorkflowName" | ForEach-Object { ($_ -split '\s+')[-1] })
if(-not $wfId){ throw "Cannot resolve workflow id for '$WorkflowName'." }
gh workflow run $wfId | Out-Null; Start-Sleep 6

$runObj = gh run list --workflow "$WorkflowName" --limit 1 --json databaseId | ConvertFrom-Json
$runId  = $runObj[0].databaseId
$stat   = (gh run view $runId --json status | ConvertFrom-Json).status
if($stat -in @('queued','in_progress')){ gh run watch $runId | Out-Host }

& .\tools\Fetch-LatestTELogs.ps1 -Workflow "$WorkflowName" -NoOpen | Out-Null
$agg=".\.reports\tradeengine_dev_tests_$runId.log"; $sum=[IO.Path]::ChangeExtension($agg,'summary.txt'); if(Test-Path $sum){ notepad $sum }

$conclusion = (gh run view $runId --json conclusion | ConvertFrom-Json).conclusion
if($conclusion -eq 'success'){
  Write-Host ("TE workflow {0}: SUCCESS  PR will auto-merge once all required checks are green." -f $runId) -ForegroundColor Green
}else{
  gh pr comment $Pr --body "Heads-up: latest TradeEngine run $runId concluded **$conclusion**. See logs under .reports/."
  Write-Warning "TradeEngine concluded $conclusion. Inspect $sum and job logs."
}

Get-ChildItem .\.reports -Filter 'tradeengine_dev_tests*.log' | Sort-Object LastWriteTime -Descending | Select-Object -Skip 10 | Remove-Item -Force
