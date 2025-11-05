# rotate_logs.ps1
Get-ChildItem "C:\Users\rhcy9\OneDrive\æ–‡ä»¶\HybridAITrading\.logs\stream_run.*.log" -ErrorAction SilentlyContinue |
  Where-Object { .LastWriteTime -lt (Get-Date).AddDays(-7) } |
  Remove-Item -Force -ErrorAction SilentlyContinue
