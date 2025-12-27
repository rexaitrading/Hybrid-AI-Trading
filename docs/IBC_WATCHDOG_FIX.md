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
Root cause: Stop-IBG scheduled task + non-persistent watcher caused IBG downtime. Fix: disable Stop-IBG task; run watcher as scheduled task; harden watcher startup logging.

Fix: Rebuilt C:\IBC\Watch-IBG-Paper.ps1 with valid [CmdletBinding()] + param at top; watcher tasks no longer exit=1; log file now created.
