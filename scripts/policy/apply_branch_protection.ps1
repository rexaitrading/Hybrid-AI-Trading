param(
  [string]$Branch = 'main',
  [int]$Approvals = 1,
  [switch]$RequireCodeOwners,
  [switch]$RequireLastPush,
  [switch]$DismissStale,
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

Write-Host "Applying protection on $owner/$repo @ $Branch" -ForegroundColor Cyan
Write-Host "Required checks:`n - tests (py3.12)"

# Base protection body
$baseBody = @{
  required_status_checks = @{ strict = $true; contexts = @('tests (py3.12)') }
  enforce_admins = $true
  restrictions   = $null
  required_pull_request_reviews = $null
  required_linear_history = $true
  allow_force_pushes = $false
  allow_deletions    = $false
  block_creations    = $false
} | ConvertTo-Json -Depth 6

# Send JSON via stdin to gh api (PowerShell-friendly)
$baseBody | gh api `
  --method PUT `
  -H "Accept: application/vnd.github+json" `
  "/repos/$owner/$repo/branches/$Branch/protection" `
  --input - | Out-Null

# PR review rules body
$prrBody = @{
  dismiss_stale_reviews           = [bool]$DismissStale
  require_code_owner_reviews      = [bool]$RequireCodeOwners
  required_approving_review_count = [int]$Approvals
  require_last_push_approval      = [bool]$RequireLastPush
  bypass_pull_request_allowances  = @{ users=@(); teams=@(); apps=@() }
} | ConvertTo-Json -Depth 6

$prrBody | gh api `
  --method PATCH `
  -H "Accept: application/vnd.github+json" `
  "/repos/$owner/$repo/branches/$Branch/protection/required_pull_request_reviews" `
  --input - | Out-Null

Write-Host " Branch protection applied." -ForegroundColor Green
