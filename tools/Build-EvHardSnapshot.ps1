[CmdletBinding()]
param(
  [Parameter(Mandatory=$false)][string]$AsOf = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

function Resolve-RepoRoot {
  # 0) Single-truth tracked pointer: .hat\repo_root.txt (preferred, ASCII-safe)
  try {
    $rootFile = Join-Path $PSScriptRoot "..\.hat\repo_root.txt"
    $rootFile = [System.IO.Path]::GetFullPath($rootFile)
    if(Test-Path -LiteralPath $rootFile){
      $s = (Get-Content -LiteralPath $rootFile -Raw -Encoding UTF8)
      if ($s.Length -gt 0 -and [int][char]$s[0] -eq 65279) { $s = $s.TrimStart([char]65279) }
      $p = $s.Trim()
      if($p){
        $full = [System.IO.Path]::GetFullPath($p)
        if(Test-Path -LiteralPath (Join-Path $full ".git")){ return $full }
        throw "[REPOROOT] .hat/repo_root.txt points to missing repo: $full"
      }
    }
  } catch { throw }

  # 1) ENV override (secondary)
  $envRoot = (($env:HAT_REPO_ROOT + "")).Trim()
  if($envRoot){
    $full = [System.IO.Path]::GetFullPath($envRoot)
    if(Test-Path -LiteralPath (Join-Path $full ".git")){ return $full }
  }

  # 2) Fallback: walk up from script location to find .git
  $d = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
  while($true){
    if(Test-Path -LiteralPath (Join-Path $d ".git")){ return $d }
    $parent = Split-Path -Parent $d
    if([string]::IsNullOrWhiteSpace($parent) -or $parent -eq $d){ break }
    $d = $parent
  }

  throw "[REPOROOT] Could not resolve repo root (.hat pointer/env/.git all failed)"
}
$root = ($s.Trim())
      if($root){
        $full = [System.IO.Path]::GetFullPath($root)
        if(Test-Path -LiteralPath (Join-Path $full "logs")){ return $full }
        if(Test-Path -LiteralPath $full){ return $full }
      }
    }
  } catch { }

  # 1) ENV override
  $envRoot = (($env:HAT_REPO_ROOT + "")).Trim()
  if($envRoot){
    $full = [System.IO.Path]::GetFullPath($envRoot)
    if(Test-Path -LiteralPath (Join-Path $full "logs")){ return $full }
    if(Test-Path -LiteralPath $full){ return $full }
  }

  # 2) fallback: walk up to find .git
  $scriptPath = $PSCommandPath
  if([string]::IsNullOrWhiteSpace($scriptPath)){ $scriptPath = $MyInvocation.MyCommand.Path }
  if([string]::IsNullOrWhiteSpace($scriptPath)){ throw "[REPOROOT] cannot resolve script path" }

  $d = Split-Path -Parent $scriptPath
  while($true){
    if(Test-Path -LiteralPath (Join-Path $d ".git")){ return $d }
    $parent = Split-Path -Parent $d
    if([string]::IsNullOrWhiteSpace($parent) -or $parent -eq $d){ break }
    $d = $parent
  }

  throw "[REPOROOT] Could not resolve repo root (no repo_root.txt, no env, no .git)"
}
if(Test-Path -LiteralPath (Join-Path $full "logs")){ return $full }
    if(Test-Path -LiteralPath $full){ return $full }
  }

  # 1) fallback: walk up from script path to find .git
  $scriptPath = $PSCommandPath
  if([string]::IsNullOrWhiteSpace($scriptPath)){ $scriptPath = $MyInvocation.MyCommand.Path }
  if([string]::IsNullOrWhiteSpace($scriptPath)){ throw "[REPOROOT] cannot resolve script path" }

  $d = Split-Path -Parent $scriptPath
  while($true){
    if(Test-Path -LiteralPath (Join-Path $d ".git")){ return $d }
    $parent = Split-Path -Parent $d
    if([string]::IsNullOrWhiteSpace($parent) -or $parent -eq $d){ break }
    $d = $parent
  }
  throw "[REPOROOT] Could not find .git and no HAT_REPO_ROOT set"
}

$repoRoot = Resolve-RepoRoot
Set-Location $repoRoot

$logs = Join-Path $repoRoot "logs"
if(-not (Test-Path $logs)){ New-Item -ItemType Directory -Force -Path $logs | Out-Null }

$today = if($AsOf){ $AsOf } else { (Get-Date).ToString("yyyy-MM-dd") }
$out   = Join-Path $logs "ev_hard_snapshot.json"

# INPUT: evidence producer output (fail-closed)
$evidence = Join-Path $logs "phase5_ev_hard_veto_evidence.json"

$ok = $false
$reason = "missing_evidence"

if(Test-Path $evidence){
  try {
    $raw = Get-Content $evidence -Raw -Encoding utf8
    if ($raw.Length -gt 0 -and [int][char]$raw[0] -eq 65279) { $raw = $raw.TrimStart([char]65279) }
    $o = $raw | ConvertFrom-Json -ErrorAction Stop
    $as = [string]$o.as_of_date
    if($as -eq $today -and [bool]$o.ok -eq $true){
      $ok = $true
      $reason = "computed_from_evidence"
      if($o.PSObject.Properties.Name -contains "reason" -and $o.reason){ $reason = [string]$o.reason }
    } else {
      $ok = $false
      $reason = "evidence_not_ok_or_stale"
    }
  } catch {
    $ok = $false
    $reason = "evidence_parse_failed"
  }
}

$payload = [ordered]@{
  ts_utc    = (Get-Date).ToUniversalTime().ToString("o")
  as_of_date= $today
  ok        = $ok
  reason    = $reason
  inputs    = [ordered]@{
    source = "phase5_ev_hard_veto_evidence.json"
  }
}

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$jsonLf = (($payload | ConvertTo-Json -Depth 6) -replace "`r`n","`n") + "`n"
[IO.File]::WriteAllText($out, $jsonLf, $utf8NoBom)

Write-Host "[EV-HARD-SNAP] wrote $out ok=$ok reason=$reason" -ForegroundColor Green
exit 0