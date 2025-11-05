# rotate_logs.ps1
Get-ChildItem "C:\Users\rhcy9\OneDrive\Ã¦â€“â€¡Ã¤Â»Â¶\HybridAITrading\.logs\stream_run.*.log" -ErrorAction SilentlyContinue |
  Where-Object { .LastWriteTime -lt (Get-Date).AddDays(-7) } |
  Remove-Item -Force -ErrorAction SilentlyContinue
