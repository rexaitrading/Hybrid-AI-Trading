# Block-G Ops Rule (console-safe)

Never dot-source a script that may call exit.

Use child-process entrypoints:
- powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Check-BlockGReady-Wrapper.ps1 -Symbol NVDA
- powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Invoke-BlockGReady.ps1 -Symbol ALL -Build

These return deterministic exit codes without killing ConsoleHost.
