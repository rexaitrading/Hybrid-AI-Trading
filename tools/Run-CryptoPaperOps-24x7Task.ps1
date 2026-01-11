[CmdletBinding()]
param(
  [int]$TickSec = 60,
  [string]$Symbols = "BTC-USD,ETH-USD",
  [int]$CooldownSec = 60
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest
chcp 65001 | Out-Null

$repoRoot="C:\HATJ\HybridAITrading"
Set-Location -LiteralPath $repoRoot
$env:HAT_REPO_ROOT = $repoRoot

$scheduledDir = Join-Path $repoRoot "logs\scheduled"
$cryptoDir    = Join-Path $repoRoot "logs\crypto"
New-Item -ItemType Directory -Path $scheduledDir -Force | Out-Null
New-Item -ItemType Directory -Path $cryptoDir -Force | Out-Null

# Rotate scheduled logs (keep tidy)
try { powershell -NoProfile -ExecutionPolicy Bypass -File ".\tools\Rotate-ScheduledLogs.ps1" -Prefix "crypto24x7_ps_" -KeepDays 14 -KeepMaxFiles 400 *> $null } catch { }

$ts = (Get-Date).ToString("yyyyMMdd_HHmmss")
$base = Join-Path $scheduledDir ("crypto24x7_ps_" + $ts)
$out  = $base + ".out.log"
$err  = $base + ".err.log"
$exit = $base + ".exit"

function LogOut([string]$m){
  $line = ("[{0}] {1}" -f (Get-Date).ToString("o"), $m)
  $line | Out-File -FilePath $out -Append -Encoding utf8
}

function LogErr([string]$m){
  $line = ("[{0}] {1}" -f (Get-Date).ToString("o"), $m)
  $line | Out-File -FilePath $err -Append -Encoding utf8
}

# ARM gate
$allowFlag = Join-Path $cryptoDir "ALLOW_SIM.txt"
if(-not (Test-Path -LiteralPath $allowFlag)){
  LogOut "[TASK] DISARMED: missing ALLOW_SIM.txt (exit 0)"
  "0" | Out-File -FilePath $exit -Encoding ascii
  exit 0
}

$env:HAT_CRYPTO_ALLOW_SIM="1"
LogOut ("[TASK] START symbols=" + $Symbols + " TickSec=" + $TickSec + " CooldownSec=" + $CooldownSec)

try {
  # call your existing runner loop
  powershell -NoProfile -ExecutionPolicy Bypass -File ".\tools\Run-CryptoPaperOps.ps1" -TickSec $TickSec -Symbols $Symbols -CooldownSec $CooldownSec 1>> $out 2>> $err
  $ec = $LASTEXITCODE
} catch {
  LogErr ("[TASK] EXCEPTION:`n" + ($_ | Out-String))
  $ec = 2
}

LogOut ("[TASK] END exit=" + $ec)
("" + $ec) | Out-File -FilePath $exit -Encoding ascii
exit $ec

