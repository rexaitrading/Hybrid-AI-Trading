<#!
.SYNOPSIS
  Apply branch protection and CI policy to a repo using GitHub CLI (gh).

.DESCRIPTION
  - Auto-discovers check runs on the latest commit of the target branch.
  - Requires status checks (always includes "tests (py3.12)"; also includes "CodeQL" if present).
  - Enables admin enforcement, linear history; disables force pushes & deletions.
  - Configures PR reviews: dismiss stale reviews = true; 1 required approval;
    require code owner reviews = true; require last push approval = true (all configurable).

.PARAMETER Branch
  Target branch (default: main)

.PARAMETER Approvals
  Required approving review count (default: 1)

.PARAMETER RequireCodeOwners
  Require CODEOWNERS reviews (default: $true)

.PARAMETER RequireLastPush
  Require last push approval (default: $true)

.PARAMETER DismissStale
  Dismiss approvals when new commits arrive (default: $true)

.PARAMETER Checks
  Explicit list of required status check context names (optional).
  If omitted, will auto-discover "tests (py3.12)" and "CodeQL" if present.

.EXAMPLE
  pwsh -File tools/apply_branch_protection.ps1

.EXAMPLE
  pwsh -File tools/apply_branch_protection.ps1 -Branch main -Approvals 1 -RequireCodeOwners $true -RequireLastPush $true -DismissStale $true
#>
[CmdletBinding()]
param(
  [string] $Branch = 'main',
  [int]    $Approvals = 1,
  [bool]   $RequireCodeOwners = $true,
  [bool]   $RequireLastPush   = $true,
  [bool]   $DismissStale      = $true,
  [string[]] $Checks = @()
)

$ErrorActionPreference = 'Stop'

function Get-RepoOwnerName {
  $remote = git remote get-url origin
  if (-not $remote) { throw "No git remote 'origin' found." }
  $repoFull = $remote -replace '^https://github.com/','' -replace '\.git$',''
  return $repoFull.Split('/')
}

function Require-GH {
  if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "GitHub CLI (gh) is required. Install from https://cli.github.com/ and run 'gh auth login'."
  }
  gh auth status | Out-Null
}

function Discover-Checks([string]$Owner,[string]$Repo,[string]$Branch) {
  $sha = (git rev-parse "origin/$Branch").Trim()
  if (-not $sha) { throw "Cannot resolve origin/$Branch SHA." }
  $cr = (gh api "repos/$Owner/$Repo/commits/$sha/check-runs?per_page=100" -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28" | ConvertFrom-Json)
  $tests = ($cr.check_runs | Where-Object { $_.app.slug -eq 'github-actions' -and $_.name -match 'tests' } | Select-Object -First 1).name
  if (-not $tests) { throw "No GH Actions check containing 'tests' found on $Branch. Run 'gh workflow run tests.yml --ref $Branch' first." }
  $ctxs = New-Object System.Collections.Generic.List[string]
  $ctxs.Add($tests) | Out-Null

  $codeql = ($cr.check_runs | Where-Object { $_.app.slug -eq 'github-actions' -and $_.name -match 'CodeQL' } | Select-Object -First 1).name
  if ($codeql) { $ctxs.Add($codeql) | Out-Null }

  return ,$ctxs.ToArray()
}

function Get-BranchProtectionRuleId([string]$Owner,[string]$Repo,[string]$Branch) {
  $q = @'
query($owner:String!, $name:String!) {
  repository(owner:$owner, name:$name) {
    id
    branchProtectionRules(first:50) { nodes { id pattern } }
  }
}
'@
  $data = gh api graphql -f query="$q" -f owner=$Owner -f name=$Repo | ConvertFrom-Json
  $repoId = $data.data.repository.id
  $rule   = $data.data.repository.branchProtectionRules.nodes | Where-Object { $_.pattern -eq $Branch } | Select-Object -First 1
  return @{ RepoId = $repoId; RuleId = $rule.id }
}

function Ensure-Rule([string]$Owner,[string]$Repo,[string]$Branch,[string[]]$Contexts,[int]$Approvals,[bool]$RequireCodeOwners,[bool]$DismissStale,[bool]$RequireLastPush) {
  $ids = Get-BranchProtectionRuleId -Owner $Owner -Repo $Repo -Branch $Branch
  $repoId = $ids.RepoId
  $ruleId = $ids.RuleId

  $reqStr = "true"
  $adm    = "true"
  $lin    = "true"
  $del    = "false"
  $force  = "false"
  $dismiss= if ($DismissStale) { "true" } else { "false" }
  $owners = if ($RequireCodeOwners) { "true" } else { "false" }

  if ($ruleId) {
    $m = @'
mutation(
  $id:ID!, $requires:Boolean!, $dismiss:Boolean!, $owners:Boolean!, $approvals:Int!, $admin:Boolean!, $linear:Boolean!, $del:Boolean!, $force:Boolean!
) {
  updateBranchProtectionRule(input:{
    branchProtectionRuleId:$id,
    requiresStatusChecks:$requires,
    dismissesStaleReviews:$dismiss,
    requiresCodeOwnerReviews:$owners,
    requiredApprovingReviewCount:$approvals,
    isAdminEnforced:$admin,
    requiresLinearHistory:$linear,
    allowsDeletions:$del,
    allowsForcePushes:$force
  }) { branchProtectionRule { id pattern } }
}
'@
    gh api graphql -f query="$m" -f id=$ruleId `
      -F requires=$reqStr -F dismiss=$dismiss -F owners=$owners -F approvals=$Approvals `
      -F admin=$adm -F linear=$lin -F del=$del -F force=$force | Out-Null
  } else {
    $m = @'
mutation(
  $repoId:ID!, $pattern:String!, $requires:Boolean!, $dismiss:Boolean!, $owners:Boolean!, $approvals:Int!, $admin:Boolean!, $linear:Boolean!, $del:Boolean!, $force:Boolean!
) {
  createBranchProtectionRule(input:{
    repositoryId:$repoId,
    pattern:$pattern,
    requiresStatusChecks:$requires,
    dismissesStaleReviews:$dismiss,
    requiresCodeOwnerReviews:$owners,
    requiredApprovingReviewCount:$approvals,
    isAdminEnforced:$admin,
    requiresLinearHistory:$linear,
    allowsDeletions:$del,
    allowsForcePushes:$force
  }) { branchProtectionRule { id pattern } }
}
'@
    gh api graphql -f query="$m" -f repoId=$repoId -f pattern=$Branch `
      -F requires=$reqStr -F dismiss=$dismiss -F owners=$owners -F approvals=$Approvals `
      -F admin=$adm -F linear=$lin -F del=$del -F force=$force | Out-Null
    $ruleId = (Get-BranchProtectionRuleId -Owner $Owner -Repo $Repo -Branch $Branch).RuleId
  }

  # Set required status check contexts (array via repeated contexts[] keys)
  $mCtx = @'
mutation($id:ID!, $contexts:[String!]!) {
  updateBranchProtectionRule(input:{
    branchProtectionRuleId:$id,
    requiredStatusCheckContexts:$contexts
  }) { branchProtectionRule { requiredStatusCheckContexts } }
}
'@
  $args = @('-f', "query=$mCtx", '-f', "id=$ruleId")
  foreach ($c in $Contexts) { $args += @('-F', "contexts[]=$c") }
  gh api graphql @args | Out-Null

  # PR Reviews sub-object (REST) – use JSON types; include last-push flag
  $prr = [ordered]@{
    dismiss_stale_reviews           = $DismissStale
    require_code_owner_reviews      = $RequireCodeOwners
    required_approving_review_count = $Approvals
    require_last_push_approval      = $RequireLastPush
  }
  ($prr | ConvertTo-Json -Depth 5) |
    gh api -X PATCH "repos/$Owner/$Repo/branches/$Branch/protection/required_pull_request_reviews" `
      -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28" --input -
}

# ---- main ----
Require-GH
$owner, $repo = Get-RepoOwnerName
if (-not $Checks -or $Checks.Count -eq 0) {
  $Checks = Discover-Checks -Owner $owner -Repo $repo -Branch $Branch
}
Write-Host "Applying protection on $owner/$repo @ $Branch" -ForegroundColor Cyan
Write-Host "Required checks:"; $Checks | ForEach-Object { " - $_" }

Ensure-Rule -Owner $owner -Repo $repo -Branch $Branch -Contexts $Checks `
  -Approvals $Approvals -RequireCodeOwners $RequireCodeOwners `
  -DismissStale $DismissStale -RequireLastPush $RequireLastPush

Write-Host "✔ Branch protection applied." -ForegroundColor Green
