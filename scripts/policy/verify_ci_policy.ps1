param(
  [string]$Branch = 'main',
  [int]$Approvals = 1,
  [switch]$RequireCodeOwners,
  [switch]$RequireLastPush,
  [switch]$FailOnMismatch = $false,
  [string]$Owner,
  [string]$Repo
)

$ErrorActionPreference='Stop'
$PSNativeCommandUseErrorActionPreference=$true
chcp 65001 > $null

function Resolve-OwnerRepo {
  param([string]$Owner,[string]$Repo)
  if ($Owner -and $Repo) { return @($Owner,$Repo) }
  try {
    $remote = (& git remote get-url origin 2>$null).Trim()
    if ($remote -and $remote -match '[:/]([^/]+)/([^/\.]+)(?:\.git)?$') {
      return @($Matches[1], $Matches[2])
    }
  } catch {}
  try {
    $r = gh repo view --json name,owner 2>$null | ConvertFrom-Json
    if ($r -and $r.owner.login -and $r.name) { return @($r.owner.login, $r.name) }
  } catch {}
  throw "Cannot resolve owner/repo. Pass -Owner and -Repo or run inside the repo."
}

$pair = Resolve-OwnerRepo -Owner $Owner -Repo $Repo
$owner,$repo = $pair[0],$pair[1]

# Fetch current protection
$protJson = gh api -H "Accept: application/vnd.github+json" "/repos/$owner/$repo/branches/$Branch/protection" 2>$null
$prrJson  = gh api -H "Accept: application/vnd.github+json" "/repos/$owner/$repo/branches/$Branch/protection/required_pull_request_reviews" 2>$null

if (-not $protJson -or -not $prrJson) {
  Write-Host " Unable to fetch protection or PRR settings for $owner/$repo@$Branch" -ForegroundColor Red
  $global:LASTEXITCODE = 1; if ($FailOnMismatch) { return } else { return }
}

$prot = $protJson | ConvertFrom-Json
$prr  = $prrJson  | ConvertFrom-Json

$checks      = ($prot.required_status_checks.contexts | Sort-Object) -join ', '
$okChecks    = $checks -like '*tests (py3.12)*'
$okApprovals = ($prr.required_approving_review_count -eq $Approvals)
$okCodeOwners= ([bool]$prr.require_code_owner_reviews -eq [bool]$RequireCodeOwners)
$okLastPush  = ([bool]$prr.require_last_push_approval -eq [bool]$RequireLastPush)

if ($okChecks -and $okApprovals -and $okCodeOwners -and $okLastPush) {
  Write-Host " Branch protection on '$Branch' matches policy." -ForegroundColor Green
  Write-Host ("  Required checks  : {0}" -f $checks)
  Write-Host ("  PR reviews       : dismiss_stale={0}, approvals={1}, codeowners={2}, last_push={3}" -f `
    $prr.dismiss_stale_reviews, $prr.required_approving_review_count, $prr.require_code_owner_reviews, $prr.require_last_push_approval)
  Write-Host ("  Admin/Linear/etc : admin={0}, linear={1}, force_push={2}, deletions={3}" -f `
    $prot.enforce_admins.enabled, $prot.required_linear_history.enabled, $prot.allow_force_pushes.enabled, $prot.allow_deletions.enabled)
} else {
  Write-Host " Policy mismatch:" -ForegroundColor Red
  Write-Host ("  checks_ok={0} approvals_ok={1} codeowners_ok={2} lastpush_ok={3}" -f $okChecks,$okApprovals,$okCodeOwners,$okLastPush)
  $global:LASTEXITCODE = 1
  if ($FailOnMismatch) { return }
}
