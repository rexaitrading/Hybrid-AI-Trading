param(
  [string]$Workflow = "tests-py312.yml",
  [int]$PR = 19,
  [int]$TimeoutMinutes = 15
)
$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot\..\..
New-Item -ItemType Directory -Force .\ci_artifacts | Out-Null

$branch = gh pr view $PR --json headRefName -q '.headRefName'
$head   = git rev-parse HEAD
$runs   = gh run list --workflow "$Workflow" --branch $branch -L 10 --json databaseId,headSha,status,conclusion | ConvertFrom-Json
$rid    = ($runs | Where-Object { $_.headSha -eq $head } | Select-Object -First 1).databaseId
if (-not $rid) { git commit --allow-empty -m "ci: kick $Workflow for $head" | Out-Null; git push | Out-Null; Start-Sleep 3; $rid = (gh run list --workflow "$Workflow" --branch $branch -L 5 --json databaseId,headSha | ConvertFrom-Json | Where-Object { $_.headSha -eq $head } | Select-Object -First 1).databaseId }
if (-not $rid) { throw "No run id for HEAD $head" }

$deadline = (Get-Date).AddMinutes($TimeoutMinutes)
do {
  $obj = (gh run view $rid --json status,conclusion,updatedAt | ConvertFrom-Json)
  Write-Host ("status={0}  conclusion={1}  updatedAt={2}" -f $obj.status,$obj.conclusion,$obj.updatedAt)
  if ($obj.status -eq 'completed') { break }
  Start-Sleep -Seconds 5
} while ((Get-Date) -lt $deadline)

# save per-job logs
$jobs = (gh run view $rid --json jobs | ConvertFrom-Json).jobs
foreach ($j in $jobs) {
  $safe = ($j.name -replace '[^\w\-]+','_')
  $dst  = ".\ci_artifacts\job_$($j.databaseId)_$safe.log"
  gh run view $rid --job $j.databaseId --log | Out-File -FilePath $dst -Encoding utf8
  Write-Host "Saved $dst (conclusion=$($j.conclusion))"
}

# summarize
if ($obj.conclusion -eq 'success') { Write-Host " $Workflow passed for HEAD $head" -ForegroundColor Green; exit 0 }
Write-Host "`n $Workflow failed. First errors:" -ForegroundColor Red
Get-ChildItem .\ci_artifacts\job_*.log | ForEach-Object {
  Write-Host "`n== $($_.Name) ==" -ForegroundColor Yellow
  Select-String -Path $_.FullName -Pattern '=== ERRORS ===|=== FAILURES ===|ERROR collecting|E\s+\w+Error:|FAILED\s+.*==' -Context 2,10 |
    Select-Object -First 60 | ForEach-Object { $_.ToString() }
}
exit 1
