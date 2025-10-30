# scripts/utils/git_helpers.ps1
# Hybrid AI Trading  Git/PR helper suite (PowerShell 5/7 compatible)

$ErrorActionPreference = 'Stop'

function Resolve-RepoRoot {
  $root = (git rev-parse --show-toplevel) 2>$null
  if (-not $root) { throw "Not inside a git repo." }
  Set-Location $root
  [Environment]::CurrentDirectory = $root
  return $root
}
function Ensure-Upstream { param([string]$Branch)
  $hasUpstream = (git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>$null)
  if (-not $hasUpstream) { git push -u origin $Branch }
}
function Show-Checks { param([int]$Number)
  gh pr view $Number --json statusCheckRollup --jq '.statusCheckRollup[] | {name,status,conclusion}'
}

function pr-open {
  param([string]$Base='main',[string]$Branch='',[switch]$AllowEmpty,[string]$Title='',[string]$Body='')
  Resolve-RepoRoot | Out-Null
  if (-not $Branch) { $Branch = (git branch --show-current) }
  if ((git branch --show-current) -ne $Branch) { git switch $Branch | Out-Null }
  git fetch origin $Base | Out-Null
  $cmp = (git rev-list --left-right --count "$Branch...origin/$Base" 2>$null) -split '\s+'
  $ahead = if ($cmp.Count -ge 1) { [int]$cmp[0] } else { 0 }

  if ($Branch -eq $Base -and $ahead -le 0) {
    if (-not $AllowEmpty) { Write-Host "Nothing to PR from '$Base'." -ForegroundColor Yellow; return }
    $new = "chore/empty-pr-" + (Get-Date -Format 'yyyyMMdd_HHmmss')
    git switch -c $new | Out-Null
    git commit --allow-empty -m "chore: empty PR seed (trigger CI)" | Out-Null
    $Branch = $new
  }
  if ($Branch -ne $Base -and $ahead -le 0) {
    if (-not $AllowEmpty) { Write-Host "Branch '$Branch' has no diff vs '$Base'." -ForegroundColor Yellow; return }
    git commit --allow-empty -m "chore: empty PR seed (trigger CI)" | Out-Null
  }
  Ensure-Upstream -Branch $Branch
  $existing = gh pr list --state open --head $Branch --json number,url --jq '.[0].url'
  if ($existing) { Write-Host "PR already open: $existing" -ForegroundColor Yellow; return }
  if ($Title -or $Body) {
    if ($Title) { $env:GH_PR_TITLE = $Title }
    if ($Body)  { $env:GH_PR_BODY  = $Body  }
    gh pr create --base $Base --head $Branch --title "$env:GH_PR_TITLE" --body "$env:GH_PR_BODY"
    Remove-Item Env:\GH_PR_TITLE,Env:\GH_PR_BODY -ErrorAction SilentlyContinue
  } else {
    gh pr create --fill --base $Base --head $Branch
  }
}

function pr-status {
  param([string]$Branch='')
  Resolve-RepoRoot | Out-Null
  if (-not $Branch) { $Branch = (git branch --show-current) }
  $pr = gh pr list --state open --head $Branch --json number,url --jq '.[0]'
  if (-not $pr) { Write-Host "No open PR for '$Branch'." -ForegroundColor Yellow; return }
  $obj = $pr | ConvertFrom-Json
  Write-Host "PR: $($obj.url)" -ForegroundColor Cyan
  Show-Checks -Number $obj.number
}

function pr-merge {
  param([Parameter(Mandatory=$true)][string]$Branch)
  Resolve-RepoRoot | Out-Null
  $pr = gh pr list --state open --head $Branch --json number --jq '.[0].number'
  if (-not $pr) {
    $merged = gh pr list --state merged --head $Branch --json number,url --jq '.[0].url'
    if ($merged) { Write-Host "Branch '$Branch' already merged: $merged" -ForegroundColor Green; return }
    $closed  = gh pr list --state closed  --head $Branch --json number,url --jq '.[0].url'
    if ($closed) { Write-Host "Branch '$Branch' has a closed PR: $closed" -ForegroundColor Yellow; return }
    throw "No open PR found for branch '$Branch'."
  }
  Show-Checks -Number $pr
  try {
    bp Temp
    gh pr merge $pr --squash --delete-branch --auto
  } catch {
    if ($_ -match 'Auto merge is not allowed') {
      Write-Host "Auto-merge disabled; falling back to direct merge..." -ForegroundColor Yellow
      gh pr merge $pr --squash --delete-branch
    } else { throw }
  } finally { bp Strict }
  git switch main | Out-Null
  git pull --ff-only | Out-Null
}

function pr-merge-safe { param([Parameter(Mandatory=$true)][string]$Branch)
  if ($Branch -eq 'main') { throw "Refusing to merge 'main'. Pass a feature branch." }
  pr-merge $Branch
}

function pr-merge-latest {
  Resolve-RepoRoot | Out-Null
  $pr = gh pr list --state open --limit 1 --json number,headRefName,url --jq '.[0].number'
  if (-not $pr) { Write-Host "No open PRs." -ForegroundColor Yellow; return }
  try { bp Temp; gh pr merge $pr --squash --delete-branch --auto } catch { gh pr merge $pr --squash --delete-branch } finally { bp Strict }
  git switch main | Out-Null
  git pull --ff-only | Out-Null
}

function git-preflight {
  param(
    [string]$Message = "chore: update",
    [string[]]$Add = @(),
    [switch]$NoCommit,
    [switch]$NoPush,
    [switch]$OpenPR,
    [string]$Base = 'main',
    [switch]$AutoBranch
  )
  Resolve-RepoRoot | Out-Null
  $branch = (git branch --show-current)
  if (-not $branch) { throw "No current branch detected." }
  if ($branch -eq 'main') {
    if (-not $AutoBranch) { throw "Refusing to commit on 'main'. Use -AutoBranch or switch to a feature branch." }
    $new = "chore/auto-preflight-" + (Get-Date -Format 'yyyyMMdd_HHmmss')
    git switch -c $new | Out-Null
    $branch = $new
    Write-Host "Auto-created feature branch: $branch" -ForegroundColor Yellow
  }

  # Sanity
  $root = (Get-Location).Path
  $rootGit = Join-Path $root ".git"
  $nested = Get-ChildItem -Recurse -Force -Directory -Filter '.git' |
            Where-Object { $_.FullName -ne $rootGit -and $_.FullName -notlike (Join-Path $root ".venv*") } |
            Select-Object -ExpandProperty FullName
  if ($nested) { throw "Suspicious nested .git:`n - $($nested -join "`n - ")" }
  if (Test-Path 'src\hybrid-ai-trading') { throw "Unexpected 'src/hybrid-ai-trading' directory present." }

  # Normalize endings
  $tracked = git ls-files -z | % { $_ }
  foreach($p in $tracked){
    try{
      $txt = Get-Content $p -Raw -ErrorAction Stop
      $lf  = ($txt -replace "`r`n","`n" -replace "`r","`n")
      if(-not $lf.EndsWith("`n")){ $lf += "`n" }
      if($lf -ne $txt){ [IO.File]::WriteAllText($p, $lf, (New-Object System.Text.UTF8Encoding($false))) }
    } catch {}
  }

  # Hooks pass 1
  pre-commit run --all-files
  if ($LASTEXITCODE -ne 0) { throw "pre-commit fixes applied; run again to verify." }

  # Stage requested or all, but ignore non-existent paths in -Add
  if ($Add.Count -gt 0) {
    $toStage = @()
    foreach($a in $Add){ if(Test-Path $a){ $toStage += $a } else { Write-Host "Skip missing path: $a" -ForegroundColor Yellow } }
    if($toStage.Count -gt 0){ git add -- $toStage } else { Write-Host "No valid -Add paths; nothing to stage." -ForegroundColor Yellow }
  } else { git add -A }

  # Hooks pass 2
  pre-commit run --all-files
  if ($LASTEXITCODE -ne 0) { throw "pre-commit failed; fix issues and re-run." }

  # Commit if needed
  $didCommit = $false
  if (-not (git diff --cached --quiet 2>$null)) { git commit -m $Message; $didCommit = $true }
  else { Write-Host "Nothing to commit (index clean)." -ForegroundColor Yellow }

  # Push/PR
  if (-not $NoPush) {
    Ensure-Upstream -Branch $branch
    if ($didCommit) { git push }
  }
  if ($OpenPR) {
    $existing = gh pr list --state open --head $branch --json number,url --jq '.[0].url'
    if ($existing) { Write-Host "PR already open: $existing" -ForegroundColor Yellow }
    else { gh pr create --fill --base $Base --head $branch }
  }

  Write-Host "Preflight complete on $branch" -ForegroundColor Green
  git status -sb
}
