@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM --- Hard anchor to repo root (based on this script location) ---
set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "REPO_ROOT=%%~fI"
pushd "%REPO_ROOT%" || exit /b 2

REM --- Absolute log dir (never relative) ---
set "LOGDIR=C:\HATJ\HybridAITrading\logs\scheduled"
if not exist "%LOGDIR%" mkdir "%LOGDIR%" >nul 2>nul

REM --- Timestamp (locale-safe) ---
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "TS=%%i"

set "BASE=%LOGDIR%\weekday_%TS%"
set "OUT=%BASE%.out.log"
set "ERR=%BASE%.err.log"
set "EXITF=%BASE%.exit"

REM --- Create logs immediately (proof-of-life) ---
echo [WRAPPER weekday v2] START ts=%TS% repo="%REPO_ROOT%" > "%OUT%"
echo [WRAPPER weekday v2] START ts=%TS% repo="%REPO_ROOT%" > "%ERR%"

REM --- Run the real launcher (append deterministically) ---
call powershell -NoProfile -ExecutionPolicy Bypass -File ".\tools\Master-Launch-Phase1to7.ps1" -Symbol NVDA 1>>"%OUT%" 2>>"%ERR%"
set "EC=%ERRORLEVEL%"

REM --- Always write exit code + propagate it ---
echo %EC% > "%EXITF%"
echo [WRAPPER weekday v2] END exit=%EC% >> "%OUT%"

popd
exit /b %EC%
