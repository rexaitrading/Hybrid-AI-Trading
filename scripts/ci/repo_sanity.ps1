$ErrorActionPreference = "Stop"

# Resolve repo root & root .git
$repoRoot = (git rev-parse --show-toplevel) 2>$null
if (-not $repoRoot) { $repoRoot = (Get-Location).Path }
$rootGit = Join-Path $repoRoot ".git"

# A) Find nested .git directories EXCEPT:
#    - the root .git itself
#    - anything under .venv (editable installs / vendor deps)
$nested = Get-ChildItem -Path $repoRoot -Recurse -Force -Directory -Filter '.git' -ErrorAction SilentlyContinue |
  Where-Object {
    ($_.FullName -ne $rootGit) -and
    ($_.FullName -notlike (Join-Path $repoRoot ".venv*"))
  } |
  Select-Object -ExpandProperty FullName

if ($nested -and $nested.Count -gt 0) {
  Write-Host "Found suspicious nested .git directories:" -ForegroundColor Red
  $nested | ForEach-Object { Write-Host " - $_" -ForegroundColor Red }
  throw "Nested .git directories detected outside .venv."
}

# B) Block accidental nested copy of repo under src/ (only check at repo root)
if (Test-Path (Join-Path $repoRoot "src\hybrid-ai-trading")) {
  throw "Unexpected 'src/hybrid-ai-trading' directory present under repo source."
}

Write-Host "Repo sanity OK." -ForegroundColor Green
