param([int]$Pr = 26)
$ErrorActionPreference = 'Stop'
$p = gh pr view $Pr --json statusCheckRollup,mergeStateStatus,number,headRefName,baseRefName,isDraft | ConvertFrom-Json
Write-Host ("PR #{0}  base:{1}  head:{2}  state:{3}  draft:{4}" -f $p.number,$p.baseRefName,$p.headRefName,$p.mergeStateStatus,$p.isDraft)

$rows = @()
if ($p.statusCheckRollup) {
  foreach ($c in $p.statusCheckRollup) {
    $rows += [pscustomobject]@{ name=$c.context; status=$c.status; conclusion=$c.conclusion; required=$c.isRequired }
  }
} else { Write-Host "No status checks yet." -ForegroundColor Yellow }

$rows | Sort-Object @{Expression='required';Descending=$true}, @{Expression='name';Descending=$false} | Format-Table -AutoSize
