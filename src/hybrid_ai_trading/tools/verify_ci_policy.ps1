<#!
.SYNOPSIS
  Verify branch protection & CI policy for a repo using GitHub CLI (gh).

.DESCRIPTION
  - Confirms required status checks include "tests (py3.12)" (and "CodeQL" if present).
  - Confirms PR review policy: dismiss stale reviews, approvals, code owners, last push approval.
  - Confirms admin enforcement, linear history, no force pushes, no deletions.
  - Exits with non-zero code if any required condition is not met.

.PARAMETER Branch
  Target branch (default: main)

.PARAMETER RequireCodeOwners
  Expect CODEOWNERS to be required (default: $true)

.PARAMETER RequireLastPush
  Expect last push approval to be required (default: $true)

.PARAMETER Approvals
  Expected required approving review count (default: 1)
#>
[CmdletBinding()]
param(
  [string] $Branch = 'main',
  [bool]   $RequireCodeOwners = $true,
  [bool]   $RequireLastPush   = $true,
  [int]    $Approvals         = 1
)

$ErrorActionPreference = 'Stop'

function Get-RepoOwnerName {
  $remote = git remote get-url origin
  if (-not $remote) { throw "No git remote 'origin' found." }
  $repoFull = $remote -replace '^https://github.com/','' -replace '\.git$',''
  return $repoFull.Split('/')
}

function Fail([string]$msg){ Write-Host "✖ $msg" -ForegroundColor Red; exit 1 }
function Ok  ([string]$msg){ Write-Host "✔ $msg" -ForegroundColor Green }

# ---- collect actuals ----
$owner, $repo = Get-RepoOwnerName

# Status checks (REST)
$rc = gh api "repos/$owner/$repo/branches/$Branch/protection/required_status_checks" `
  -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28" | ConvertFrom-Json
$contexts = @()
if ($rc -and $rc.contexts) { $contexts = @($rc.contexts) }

# PR review settings (REST)
$pr = gh api "repos/$owner/$repo/branches/$Branch/protection/required_pull_request_reviews" `
  -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28" | ConvertFrom-Json

# Aggregated (GraphQL)
$q = @'
query($owner:String!, $name:String!) {
  repository(owner:$owner, name:$name) {
    branchProtectionRules(first:50) {
      nodes {
        pattern
        requiresStatusChecks
        requiredStatusCheckContexts
        dismissesStaleReviews
        requiresCodeOwnerReviews
        requiredApprovingReviewCount
        allowsDeletions
        allowsForcePushes
        requiresLinearHistory
        isAdminEnforced
      }
    }
  }
}
'@
$rules = (gh api graphql -f query="$q" -f owner=$owner -f name=$repo | ConvertFrom-Json).data.repository.branchProtectionRules.nodes
$rule  = $rules | Where-Object { $_.pattern -eq $Branch } | Select-Object -First 1
if (-not $rule) { Fail "No branch protection rule found for '$Branch'." }

# ---- expectations & checks ----
# Always require tests (py3.12)
if (-not ($contexts -contains 'tests (py3.12)')) {
  Fail "Missing required status check: 'tests (py3.12)'. Actual: $($contexts -join ', ')"
}

# If CodeQL check run exists in contexts list, it must be present
$expectsCodeQL = ($contexts -match '^CodeQL$').Count -gt 0
if ($expectsCodeQL -and -not ($contexts -contains 'CodeQL')) {
  Fail "CodeQL is present in checks but not required. Actual: $($contexts -join ', ')"
}

# PR reviews enforcement
if (-not $pr) { Fail "PR review protection block missing (REST endpoint returned empty)." }

if (-not $pr.dismiss_stale_reviews) { Fail "dismiss_stale_reviews is not enabled." }
if ($pr.required_approving_review_count -ne $Approvals) { Fail "Approvals required = $($pr.required_approving_review_count), expected $Approvals." }
if ($RequireCodeOwners -and -not $pr.require_code_owner_reviews) { Fail "require_code_owner_reviews should be enabled." }
if (-not $RequireCodeOwners -and $pr.require_code_owner_reviews) { Fail "require_code_owner_reviews is enabled but expected disabled." }
if ($RequireLastPush -and -not $pr.require_last_push_approval) { Fail "require_last_push_approval should be enabled." }
if (-not $RequireLastPush -and $pr.require_last_push_approval) { Fail "require_last_push_approval is enabled but expected disabled." }

# Admin / linear / safety flags (GraphQL)
if (-not $rule.isAdminEnforced)    { Fail "Admin enforcement is not enabled." }
if (-not $rule.requiresLinearHistory) { Fail "Linear history is not required." }
if ($rule.allowsForcePushes)       { Fail "Force pushes are allowed (should be disabled)." }
if ($rule.allowsDeletions)         { Fail "Branch deletions are allowed (should be disabled)." }

Ok "Branch protection on '$Branch' matches policy."
Write-Host "  Required checks  : $($contexts -join ', ')"
Write-Host "  PR reviews       : dismiss_stale=$($pr.dismiss_stale_reviews), approvals=$($pr.required_approving_review_count), codeowners=$($pr.require_code_owner_reviews), last_push=$($pr.require_last_push_approval)"
Write-Host "  Admin/Linear/etc : admin=$($rule.isAdminEnforced), linear=$($rule.requiresLinearHistory), force_push=$($rule.allowsForcePushes), deletions=$($rule.allowsDeletions)"
exit 0
