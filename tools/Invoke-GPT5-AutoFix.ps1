param(
  [string]$Model         = "gpt-5",
  [ValidateSet("low","medium","high")][string]$Effort = "medium",
  [int]   $MaxTokens     = 1200,
  [string]$TestCmd       = "python -m pytest -q tests --maxfail=1 --ignore=tests/integration --disable-warnings -s",
  [string]$RepoRoot      = "C:\Dev\HybridAITrading",
  [int]   $MaxIterations = 10
)

$ErrorActionPreference = 'Stop'

function Invoke-External {
  param([string]$CommandLine)

  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName               = 'cmd.exe'
  $psi.Arguments              = '/d /c ' + $CommandLine
  $psi.WorkingDirectory       = $RepoRoot
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError  = $true
  $psi.UseShellExecute        = $false
  $psi.CreateNoWindow         = $true

  $p = [System.Diagnostics.Process]::Start($psi)
  $out = $p.StandardOutput.ReadToEnd()
  $err = $p.StandardError.ReadToEnd()
  $p.WaitForExit()

  [pscustomobject]@{
    ExitCode = $p.ExitCode
    Output   = ($out + [Environment]::NewLine + $err).TrimEnd()
  }
}

function Write-Section([string]$Text) {
  Write-Host ""
  Write-Host ("=== {0} ===" -f $Text) -ForegroundColor Cyan
  Write-Host ""
}

# --- Main ---
if (-not (Test-Path -LiteralPath $RepoRoot)) {
  throw "RepoRoot not found: $RepoRoot"
}

Set-Location -LiteralPath $RepoRoot
Write-Host ("PWD: {0}" -f (Resolve-Path .)) -ForegroundColor DarkCyan

if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot 'tests'))) {
  Write-Warning ("No 'tests' directory under {0}. Listing *_test.py / test_*.py under repo..." -f $RepoRoot)
  Get-ChildItem -Recurse -Include test_*.py,*_test.py | ForEach-Object { Write-Host (" - " + $_.FullName) }
}

for ($i = 1; $i -le $MaxIterations; $i++) {
  Write-Section ("Run {0}/{1} : executing tests..." -f $i, $MaxIterations)

  $run      = Invoke-External -CommandLine $TestCmd
  $output   = $run.Output
  $exitCode = $run.ExitCode

  if ($output) { $output | Write-Host }

  if ($exitCode -eq 0) {
    Write-Host "Tests GREEN " -ForegroundColor Green
    exit 0
  }

  Write-Warning ("Tests failed (exit {0}). Stopping after first attempt." -f $exitCode)
  exit $exitCode
}

exit 1
