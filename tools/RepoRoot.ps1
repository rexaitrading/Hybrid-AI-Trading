Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

function Get-RepoRoot {
  # Prefer current working directory (already Unicode-correct in this session)
  try {
    $p = (Resolve-Path .).Path
    if (Test-Path -LiteralPath (Join-Path $p ".git")) { return $p }
  } catch {}

  # Fallback: derive from this script's path (tools\RepoRoot.ps1 -> repo root)
  try {
    if ($PSCommandPath) {
      return (Split-Path -Parent (Split-Path -Parent $PSCommandPath))
    }
  } catch {}

  throw "Cannot determine repo root (Unicode-safe)."
}

