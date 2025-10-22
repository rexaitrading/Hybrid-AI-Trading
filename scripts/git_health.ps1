$ErrorActionPreference='Stop'; Set-StrictMode -Version Latest

function Write-Section([string]$t){ $bar=('='*78); Write-Host "`n$bar`n# $t`n$bar" }
function Out-Both([string]$s){ $null=$script:Buf.AppendLine($s); Write-Host $s }

$Buf = New-Object System.Text.StringBuilder
$root=(Get-Location).Path
$report = Join-Path $root "__git_health.txt"

Write-Section "Git & repo sanity"
$gitVer = (& git --version) 2>$null
Out-Both ("git version = {0}" -f (($gitVer -join ' ') -replace '\s+',' '))
$inside = (& git rev-parse --is-inside-work-tree) 2>$null
Out-Both ("inside work tree = {0}" -f $inside)
$toplevel = (& git rev-parse --show-toplevel) 2>$null
Out-Both ("toplevel = {0}" -f $toplevel)

Write-Section "Status (short) + ahead/behind"
$statusShort = (& git status -sb) 2>$null
$statusPorc  = (& git status --porcelain=v2) 2>$null
Out-Both (($statusShort | Out-String))

$branch   = (& git rev-parse --abbrev-ref HEAD) 2>$null
$upstream = (& git rev-parse --abbrev-ref --symbolic-full-name '@{u}') 2>$null
if ($LASTEXITCODE -eq 0 -and $upstream) {
  $ahead = (& git rev-list --left-right --count "$upstream...HEAD") 2>$null
  if ($ahead) {
    $parts = $ahead -split '\s+'
    Out-Both ("upstream = {0} | behind={1} ahead={2}" -f $upstream,$parts[0],$parts[1])
  } else { Out-Both ("upstream = {0}" -f $upstream) }
} else {
  Out-Both ("branch = {0} (no upstream tracking)" -f $branch)
}

Write-Section "Remotes"
$rem = (& git remote -v) 2>$null
Out-Both ($rem | Out-String)

Write-Section "Branches (vv)"
$branches = (& git branch -vv --no-abbrev) 2>$null
Out-Both ($branches | Out-String)

Write-Section "Recent commits (last 20)"
$log = (& git log --oneline --decorate --graph -n 20) 2>$null
Out-Both ($log | Out-String)

Write-Section "Stash list"
$stash = (& git stash list) 2>$null
if ($stash) { Out-Both ($stash | Out-String) } else { Out-Both "(none)" }

Write-Section "Recent tags"
$tags = (& git tag --sort=-creatordate) 2>$null | Select-Object -First 5
if ($tags) { Out-Both ($tags | Out-String) } else { Out-Both "(none)" }

Write-Section "Configs (autocrlf, safecrlf, ignores)"
$autocrlf = (& git config --get core.autocrlf) 2>$null
$safecrlf = (& git config --get core.safecrlf) 2>$null
$excludes = (& git config --get core.excludesfile) 2>$null
Out-Both ("core.autocrlf     = {0}" -f $(if ($autocrlf) { $autocrlf } else { '(unset)' }))
Out-Both ("core.safecrlf     = {0}" -f $(if ($safecrlf) { $safecrlf } else { '(unset)' }))
Out-Both ("core.excludesfile = {0}" -f $(if ($excludes) { $excludes } else { '(unset)' }))

Write-Section "Working tree changes (porcelain=v2 summary)"
if ($statusPorc) {
  $added   = @($statusPorc | Select-String '^1 .* A ' -AllMatches).Count
  $mod     = @($statusPorc | Select-String '^1 .* M ' -AllMatches).Count
  $ren     = @($statusPorc | Select-String '^2 '        -AllMatches).Count
  $untrk   = @($statusPorc | Select-String '^\? '       -AllMatches).Count
  $unmerg  = @($statusPorc | Select-String '^u '        -AllMatches).Count
} else {
  $added = $mod = $ren = $untrk = $unmerg = 0
}
Out-Both ("added={0} modified={1} renamed={2} untracked={3} unmerged={4}" -f $added,$mod,$ren,$untrk,$unmerg)

Write-Section "Diff --stat (unstaged)"
$stat = (& git diff --stat) 2>$null
if ($stat){ Out-Both ($stat | Out-String) } else { Out-Both "(no unstaged diffs)" }

Write-Section "Diff --stat (staged)"
$statStaged = (& git diff --cached --stat) 2>$null
if ($statStaged){ Out-Both ($statStaged | Out-String) } else { Out-Both "(no staged diffs)" }

Write-Section "Conflict markers scan (working tree)"
$conf = Get-ChildItem -Recurse -File -ErrorAction SilentlyContinue |
  Where-Object { $_.FullName -notmatch '\\\.git\\|\\\.venv\\|\\logs\\|\\__pycache__\\' } |
  Select-String -Pattern '^(<<<<<<<|>>>>>>>)' -SimpleMatch -AllMatches -ErrorAction SilentlyContinue
if ($conf){ 
  ($conf | Select-Object Path,LineNumber,Line | Format-Table -Auto | Out-String) | ForEach-Object { Out-Both $_ }
} else { Out-Both "(no conflict markers found)" }

Write-Section "Large files (>100 MB) in working tree"
$large = Get-ChildItem -Recurse -File -ErrorAction SilentlyContinue |
  Where-Object { $_.Length -gt 100MB -and $_.FullName -notmatch '\\\.git\\|\\\.venv\\' } |
  Sort-Object Length -Descending | Select-Object -First 20 FullName,Length
if ($large){ $large | Format-Table -Auto | Out-String | ForEach-Object { Out-Both $_ } } else { Out-Both "(none >100MB outside .venv/.git)" }

Write-Section "Git LFS (tracked files)"
try {
  $lfs = (& git lfs ls-files) 2>$null
  if ($lfs){ Out-Both ($lfs | Out-String) } else { Out-Both "(none or LFS not used)" }
} catch { Out-Both "(git-lfs not installed)" }

[IO.File]::WriteAllText($report, $Buf.ToString(), [Text.UTF8Encoding]::new($false))
Out-Both ("`nSaved report: {0}" -f $report)
