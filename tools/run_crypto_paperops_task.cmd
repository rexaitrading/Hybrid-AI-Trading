@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "REPO_ROOT=%%~fI"
pushd "%REPO_ROOT%" || exit /b 2

set "LOGDIR=C:\HATJ\HybridAITrading\logs\scheduled"
if not exist "%LOGDIR%" mkdir "%LOGDIR%" >nul 2>nul

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "TS=%%i"

set "BASE=%LOGDIR%\crypto_%TS%"
set "OUT=%BASE%.out.log"
set "ERR=%BASE%.err.log"
set "EXITF=%BASE%.exit"

echo [WRAPPER crypto v1] START ts=%TS% repo="%REPO_ROOT%" > "%OUT%"
echo [WRAPPER crypto v1] START ts=%TS% repo="%REPO_ROOT%" > "%ERR%"

REM ---- SIM ONLY: allow is controlled by env var ----

REM ---- Runtime config (env overrides) ----
if not defined HAT_CRYPTO_SYMBOLS set "HAT_CRYPTO_SYMBOLS=BTC-USD,ETH-USD"
if not defined HAT_CRYPTO_TICKSEC set "HAT_CRYPTO_TICKSEC=60"
if not defined HAT_CRYPTO_COOLDOWN_SEC set "HAT_CRYPTO_COOLDOWN_SEC=0"

if exist "%ALLOW_FLAG%" set "HAT_CRYPTO_ALLOW_SIM=1"

call powershell -NoProfile -ExecutionPolicy Bypass -File ".\tools\Run-CryptoPaperOps.ps1" -Once -TickSec %HAT_CRYPTO_TICKSEC% -Symbols "%HAT_CRYPTO_SYMBOLS%" -CooldownSec %HAT_CRYPTO_COOLDOWN_SEC% 1>>"%OUT%" 2>>"%ERR%"
set "EC=%ERRORLEVEL%"

echo %EC% > "%EXITF%"
echo [WRAPPER crypto v1] END exit=%EC% >> "%OUT%"

popd
exit /b %EC%
