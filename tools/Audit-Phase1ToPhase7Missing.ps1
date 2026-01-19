[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $repoRoot

$outMd   = ".\logs\audit_phase1_to_phase7_missing.md"
$outJson = ".\logs\audit_phase1_to_phase7_missing.json"
New-Item -ItemType Directory -Force -Path ".\logs" | Out-Null

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$mdFull  = [System.IO.Path]::GetFullPath($outMd)
$jsFull  = [System.IO.Path]::GetFullPath($outJson)

# hard reset md
[System.IO.File]::WriteAllText($mdFull, "", $utf8NoBom)

function W([string]$s){
  [System.IO.File]::AppendAllText($mdFull, ($s + "`n"), $utf8NoBom)
}

$global:__J = [ordered]@{
  ts_utc = (Get-Date).ToUniversalTime().ToString("o")
  items  = @()
}

function JAdd([hashtable]$h){
  $global:__J.items += @([pscustomobject]$h)
}

W "# Phase-1 to Phase-7 Audit (Missing + Upgrade Opportunities)"
W ""
W ("- Generated: {0}" -f (Get-Date).ToString("yyyy-MM-dd HH:mm:ss"))
W ""

# A) Git / Workspace Hygiene
W "## A) Git / Workspace Hygiene"
$st = @(git status --porcelain)

if($st.Count -eq 0){
  W "- OK Clean working tree"
  JAdd @{ area="git"; check="status_clean"; ok=$true; detail="" }
} else {
  $stLines = @($st | ForEach-Object { $_ + "" })
  W "- WARN Uncommitted/untracked present"
  W "```"
  foreach($line in $stLines){ W $line }
  W "```"
  JAdd @{ area="git"; check="status_clean"; ok=$false; detail=($stLines -join "`n") }

  $untracked = @($stLines | Where-Object { $_ -match '^\?\?' })
  if($untracked.Count -gt 0){
    W "- WARN Untracked files:"
    foreach($u in $untracked){ W ("  - " + $u) }
    JAdd @{ area="git"; check="untracked_present"; ok=$false; detail=($untracked -join "`n") }
  } else {
    JAdd @{ area="git"; check="untracked_present"; ok=$true; detail="" }
  }
}

# B) Block-G Contract (Authoritative)
W ""
W "## B) Block-G Contract (Authoritative)"

$bgOut  = powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Build-BlockGStatusStub.ps1 -Market $env:HAT_MARKET -Symbol ALL 2>&1
$bgExit = $LASTEXITCODE
W ("- Build-BlockGStatusStub exit={0}" -f $bgExit)
JAdd @{ area="blockg"; check="builder_exit0"; ok=($bgExit -eq 0); detail=($bgOut | Out-String) }

$cp = ".\logs\blockg_status_stub.json"
if(Test-Path $cp){
  $stj = Get-Content -LiteralPath $cp -Encoding UTF8 -Raw | ConvertFrom-Json
  $nv = [bool]$stj.nvda_blockg_ready
  W ("- nvda_blockg_ready={0}" -f $nv)

  $reasons = @($stj.reasons_not_ready)
  if($reasons.Count -gt 0){
    W "- reasons_not_ready:"
    foreach($r in $reasons){ W ("  - " + $r) }
  }
  JAdd @{ area="blockg"; check="nvda_ready"; ok=$nv; detail=(@($reasons) -join "; ") }
} else {
  W "- MISSING logs\\blockg_status_stub.json"
  JAdd @{ area="blockg"; check="contract_exists"; ok=$false; detail=$cp }
}

# Write JSON summary
$jtxt = ($global:__J | ConvertTo-Json -Depth 8)
[System.IO.File]::WriteAllText($jsFull, ($jtxt -replace "`r`n","`n") + "`n", $utf8NoBom)

W ""
W "---"
W "Generated files:"
W ("- {0}" -f $mdFull)
W ("- {0}" -f $jsFull)

"OK wrote:`n$outMd`n$outJson" | Out-Host
