Param(
  [ValidateSet('Temp','Strict','View')]
  [string]$Mode = 'View',
  [string]$Branch = 'main',
  [string]$CheckContext = 'tests (py3.12)',
  [switch]$PauseOnExit
)

$ErrorActionPreference = 'Stop'
function Write-Utf8NoBom($Path, $Text){ [IO.File]::WriteAllText($Path, $Text, (New-Object System.Text.UTF8Encoding($false))) }

try {
  # Prefer repo autodetect; fall back to explicit owner/repo if not in a Git dir
  $repo = (gh repo view --json nameWithOwner --jq .nameWithOwner) 2>$null
  if (-not $repo) { $repo = 'rexaitrading/Hybrid-AI-Trading' }

  if ($Mode -eq 'View') {
    gh api -H "Accept: application/vnd.github+json" "repos/$repo/branches/$Branch/protection"
    return
  }

  $payloadTemp = @"
{
  "required_status_checks": { "strict": true, "checks": [ { "context": "$CheckContext" } ] },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false,
    "required_approving_review_count": 0,
    "require_last_push_approval": false
  },
  "restrictions": null,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false
}
"@

  $payloadStrict = @"
{
  "required_status_checks": { "strict": true, "checks": [ { "context": "$CheckContext" } ] },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": true,
    "required_approving_review_count": 1,
    "require_last_push_approval": true
  },
  "restrictions": null,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false
}
"@

  $tmp = Join-Path $env:TEMP "bp_apply.json"
  Write-Utf8NoBom $tmp ($(if ($Mode -eq 'Temp') { $payloadTemp } else { $payloadStrict }))

  gh api --method PUT -H "Accept: application/vnd.github+json" "repos/$repo/branches/$Branch/protection" --input $tmp | Out-Null
  Write-Host "Applied $Mode policy on $repo@$Branch with check '$CheckContext'." -ForegroundColor Green
}
catch { Write-Error $_ }
finally {
  if ($PauseOnExit -and -not $env:CI) { Read-Host "Done. Press Enter to close" }
}
