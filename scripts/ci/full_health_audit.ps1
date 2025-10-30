param()
$ErrorActionPreference = "Stop"

function Out-Json($o){ $o | ConvertTo-Json -Depth 6 }

$root = (git rev-parse --show-toplevel) 2>$null
if (-not $root) { throw "Not in a git repo" }
Set-Location $root
[Environment]::CurrentDirectory = (Get-Location).Path

$problems = [System.Collections.Generic.List[string]]::new()

# A) Stray nested repo dir
if (Test-Path "src\hybrid-ai-trading") {
  $problems.Add("Stray 'src/hybrid-ai-trading' directory exists.")
}

# B) Nested .git outside .venv
$rootGit = Join-Path $root ".git"
$nested = Get-ChildItem -Path $root -Recurse -Force -Directory -Filter ".git" -ErrorAction SilentlyContinue |
  Where-Object { $_.FullName -ne $rootGit -and $_.FullName -notlike (Join-Path $root ".venv*") } |
  Select-Object -ExpandProperty FullName
if ($nested){ $problems.Add("Suspicious nested .git: `n - " + ($nested -join "`n - ")) }

# C) Files missing trailing newline (common EOF hook trigger)
$noFinalNl = @()
git ls-files -z | % { $_ } | ForEach-Object {
  $p = $_
  try{
    $bytes = [IO.File]::ReadAllBytes($p)
    if ($bytes.Length -gt 0 -and $bytes[-1] -ne 0x0A) { $noFinalNl += $p }
  } catch {}
}
if ($noFinalNl){ $problems.Add("Files missing final newline:`n - " + ($noFinalNl -join "`n - ")) }

# D) CRLF in tracked text files (should be LF)
$crlf = @()
git ls-files -z | % { $_ } | ForEach-Object {
  $p = $_
  try{
    $txt = Get-Content $p -Raw -ErrorAction Stop
    if ($txt -match "`r`n") { $crlf += $p }
  } catch {}
}
# Filter out obvious binaries by extension
$crlf = $crlf | ? { $_ -notmatch '\.(png|jpg|jpeg|gif|pdf|ico|zip|gz|7z|exe|dll|pyd|whl)$' }
if ($crlf){ $problems.Add("Files still contain CRLF line endings:`n - " + ($crlf -join "`n - ")) }

# E) pre-commit status
$pre = & pre-commit run --all-files 2>&1
$preOk = $LASTEXITCODE -eq 0

# F) Branch protection + open PR statuses
$prot = gh api -H "Accept: application/vnd.github+json" repos/:owner/:repo/branches/main/protection 2>$null
$prs  = gh pr list --state open --json number,title,headRefName,baseRefName,url 2>$null
$checks = $null
if ($prs){
  $checks = @()
  ($prs | ConvertFrom-Json) | % {
    $c = gh pr view $_.number --json statusCheckRollup 2>$null
    $checks += [pscustomobject]@{ number=$_.number; url=$_.url; checks=$c }
  }
}

$result = [pscustomobject]@{
  root        = $root
  problems    = $problems
  precommitOK = $preOk
  protection  = if($prot){ (ConvertFrom-Json $prot) } else { $null }
  openPRs     = if($prs){ (ConvertFrom-Json $prs) } else { @() }
  prChecks    = $checks
}

$result | Out-Json
if ($problems.Count -gt 0 -or -not $preOk) { exit 1 }
