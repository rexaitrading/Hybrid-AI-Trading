[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSCommandPath
$archiveRoot = Join-Path $repoRoot "archive_phase5_bak"

Write-Host "[BACKUP] Organizing Phase-5 EV-related backup files into $archiveRoot" -ForegroundColor Cyan

$patterns = @(
    "config\phase5\*ev*.bak*",
    "config\phase5\*phase5_ev_bands*.bak*",
    "tools\*Ev*.bak*",
    "tools\*Phase5*.bak*"
)

foreach ($pat in $patterns) {
    $glob = Join-Path $repoRoot $pat
    Get-ChildItem $glob -File -ErrorAction SilentlyContinue | ForEach-Object {
        $src = $_.FullName
        $rel = $src.Substring($repoRoot.Length).TrimStart('\','/')
        $dest = Join-Path $archiveRoot $rel

        $destDir = Split-Path -Parent $dest
        if (-not (Test-Path $destDir)) {
            New-Item -ItemType Directory -Path $destDir -Force | Out-Null
        }

        Write-Host "[MOVE] $rel -> $($dest.Substring($repoRoot.Length))" -ForegroundColor Yellow
        Move-Item $src $dest
    }
}

Write-Host "[BACKUP] Phase-5 EV-related backups organized under archive_phase5_bak." -ForegroundColor Green