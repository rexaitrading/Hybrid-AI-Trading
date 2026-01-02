@echo off
REM [HAT] Repo guard: never run global pytest.exe
echo.
echo [HAT] FAIL-CLOSED: Do NOT run global pytest.exe.
echo [HAT] Use: tools\pytest.ps1 %*
echo.
exit /b 2
