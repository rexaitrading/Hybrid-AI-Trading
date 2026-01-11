@echo off
set LOGDIR=C:\HATJ\HybridAITrading\logs\scheduled
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
set TS=%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TS=%TS: =0%
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\HATJ\HybridAITrading\tools\Weekend-Launch.ps1" -Symbol NVDA -RunCrypto 1> "%LOGDIR%\weekend_%TS%.out.log" 2> "%LOGDIR%\weekend_%TS%.err.log"
echo %errorlevel% > "%LOGDIR%\weekend_%TS%.exit"
