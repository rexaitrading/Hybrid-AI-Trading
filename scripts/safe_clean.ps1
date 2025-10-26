param(
  [switch]$DryRun
)
$ex = @('-e','.venv/','-e','.venv/*','-e','.pytest_cache/','-e','.ruff_cache/')
$cmd = @('git','clean','-fdX') + $ex
if ($DryRun) { $cmd += '-n' }
Write-Host "Running: $($cmd -join ' ')" -ForegroundColor Yellow
& $cmd
