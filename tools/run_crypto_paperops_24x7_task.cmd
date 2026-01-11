@echo off
setlocal EnableExtensions

REM ---- Bootstrap log (always works) ----
set "BOOTLOG=C:\HATJ\HybridAITrading\logs\scheduled\crypto24x7_BOOT.log"
echo [BOOT] start > "%BOOTLOG%"
echo [BOOT] VERSION VSTAMP_20260110_185652 >> "%BOOTLOG%"
REM ---- Compute paths ----
set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "REPO_ROOT=%%~fI"

set "LOGDIR=C:\HATJ\HybridAITrading\logs\scheduled"
if not exist "%LOGDIR%" mkdir "%LOGDIR%" >>"%BOOTLOG%" 2>&1

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "TS=%%i"
if "%TS%"=="" (echo [BOOT] TS_EMPTY >>"%BOOTLOG%" & exit /b 255)

set "BASE=%LOGDIR%\crypto24x7_%TS%"
set "OUT=%BASE%.out.log"
set "ERR=%BASE%.err.log"
set "EXITF=%BASE%.exit"

echo [BOOT] OUT=%OUT% >>"%BOOTLOG%"
echo [BOOT] ERR=%ERR% >>"%BOOTLOG%"

REM ---- Start logs ----
echo [WRAPPER crypto24x7 v1] START ts=%TS% repo="%REPO_ROOT%" > "%OUT%"
echo [WRAPPER crypto24x7 v1] START ts=%TS% repo="%REPO_ROOT%" > "%ERR%"
echo [WRAPPER crypto24x7 v1] VERSION VSTAMP_20260110_185652 >> "%OUT%"
pushd "%REPO_ROOT%"
echo [WRAPPER crypto24x7 v1] PUSHD_EC=%ERRORLEVEL% CWD=%CD% >> "%OUT%"
if not "%ERRORLEVEL%"=="0" (echo 2 > "%EXITF%" & echo [WRAPPER] PUSHD_FAIL >> "%OUT%" & popd & exit /b 2)

REM ---- ARM/DISARM ----
set "ALLOW_FLAG=C:\HATJ\HybridAITrading\logs\crypto\ALLOW_SIM.txt"
set "HAT_CRYPTO_ALLOW_SIM=0"
if exist "%ALLOW_FLAG%" set "HAT_CRYPTO_ALLOW_SIM=1"
echo [WRAPPER] ALLOW_FLAG="%ALLOW_FLAG%" >> "%OUT%"
if exist "%ALLOW_FLAG%" (echo [WRAPPER] ALLOW_EXISTS=YES>>"%OUT%") else (echo [WRAPPER] ALLOW_EXISTS=NO>>"%OUT%")
echo [WRAPPER] HAT_CRYPTO_ALLOW_SIM=%HAT_CRYPTO_ALLOW_SIM% >> "%OUT%"

if not exist "%ALLOW_FLAG%" (echo [WRAPPER] DISARMED (missing ALLOW_SIM.txt) >> "%OUT%" & echo 0 > "%EXITF%" & popd & exit /b 0)

REM ---- Runtime config (env overrides) ----
if not defined HAT_CRYPTO_SYMBOLS set "HAT_CRYPTO_SYMBOLS=BTC-USD,ETH-USD"
if not defined HAT_CRYPTO_TICKSEC set "HAT_CRYPTO_TICKSEC=60"
if not defined HAT_CRYPTO_COOLDOWN_SEC set "HAT_CRYPTO_COOLDOWN_SEC=60"
echo [WRAPPER] PRECALL Run-CryptoPaperOps >> "%OUT%"
call powershell -NoProfile -ExecutionPolicy Bypass -File ".\tools\Run-CryptoPaperOps.ps1" -Once -TickSec %HAT_CRYPTO_TICKSEC% -Symbols "%HAT_CRYPTO_SYMBOLS%" -CooldownSec %HAT_CRYPTO_COOLDOWN_SEC% 1>>"%OUT%" 2>>"%ERR%"
set "EC=%ERRORLEVEL%"
echo [WRAPPER] POSTCALL EC=%EC% >> "%OUT%"
echo %EC% > "%EXITF%"
echo [WRAPPER] END exit=%EC% >> "%OUT%"
popd
exit /b %EC%
