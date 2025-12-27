IBC WATCHDOG FIX  PAPER (C:\IBC\Watch-IBG-Paper.ps1)

Root cause:
- Old watcher used wildcard kill: Stop-Process -Name tws, ibgateway* -Force
- This can terminate healthy IBG during brief port blips/startup.

Fix:
- Removed wildcard kill
- Only stops exact ibgateway/ibgateway1 PID when port is not listening AND uptime >= MinUptimeSec
- Added backoff + reasoned log to C:\IBC\ibg_watch_paper.log

Rollback:
- Restore the backup file created during patch:
  C:\IBC\Watch-IBG-Paper.ps1.bak_safe_restart_YYYYMMDD_HHMMSS