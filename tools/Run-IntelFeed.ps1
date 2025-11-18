param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = 'Stop'

# toolsDir = ...\HybridAITrading\tools
$toolsDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $toolsDir) { $toolsDir = Get-Location }

# root = ...\HybridAITrading
$root = Split-Path -Parent $toolsDir
Set-Location $root

# Hydrate YOUTUBE_API_KEY from User-level env for this process
$env:YOUTUBE_API_KEY = [Environment]::GetEnvironmentVariable('YOUTUBE_API_KEY','User')

# 1) Refresh YouTube intel (403-safe, keeps last good file)
& $PythonExe .\tools\yt_scalper_feed.py

# 2) Refresh News intel
& $PythonExe .\tools\news_feed.py