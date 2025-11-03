$ErrorActionPreference = 'Stop'

# path of this guard
$self = (Resolve-Path $MyInvocation.MyCommand.Path).Path.ToLower()

# scan only text-like file types
$exts = @('.py','.ps1','.psm1','.psd1','.yml','.yaml','.json','.md','.txt','.ini','.cfg','.toml')

# collect candidates, excluding noisy trees and this file
$files = Get-ChildItem -Recurse -File | Where-Object {
    ($exts -contains $_.Extension.ToLower()) -and
    $_.FullName.ToLower() -ne $self -and
    $_.FullName -notmatch '\\\.git\\'          -and
    $_.FullName -notmatch '\\\.venv\\'         -and
    $_.FullName -notmatch '\\\.artifacts\\'    -and
    $_.FullName -notmatch '\\\.logs\\'         -and
    $_.FullName -notmatch '\\\.pytest_cache\\' -and
    $_.FullName -notmatch '\\build\\'          -and
    $_.FullName -notmatch '\\dist\\'           -and
    $_.FullName -notmatch '\\\.egg-info\\'
}

# search for literal backtick-r-backtick-n
$hits = foreach ($f in $files) {
    Select-String -Path $f.FullName -Pattern '``r``n' -SimpleMatch -AllMatches -ErrorAction SilentlyContinue
}

if ($hits) {
    $hits | ForEach-Object { '{0}:{1}: {2}' -f $_.Path,$_.LineNumber,$_.Line }
    Write-Error 'Literal `` `r`` `n`` found. Use LF newlines; do not inject backticks.'
    exit 1
}

Write-Host 'Guard OK: no literal `` `r`` `n`` sequences.' -ForegroundColor Green
