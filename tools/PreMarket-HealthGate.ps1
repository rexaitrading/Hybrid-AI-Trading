$ErrorActionPreference='Stop'
. C:\Dev\HybridAITrading\tools\Notion-Journal.ps1

$DbId = (Get-Content C:\Dev\HybridAITrading\secrets\trading_journal_dbid.txt -Raw).Trim()
try { Test-NotionHealth -DbId $DbId } catch {
  try {
    if ($env:SLACK_BOT_TOKEN -and $env:SLACK_CHANNEL_ID) {
      Invoke-Slack -Method 'chat.postMessage' -Body @{ channel=$env:SLACK_CHANNEL_ID; text=" Notion health failed on $env:COMPUTERNAME. Skipping journaling; proceeding with ORB smoke." }
    }
  } catch {}
}
Set-Location C:\Dev\HybridAITrading
if (Test-Path .\.venv\Scripts\activate.ps1) { . .\.venv\Scripts\activate.ps1 }
python -m pytest -q tests\smoke\orb_smoke.py -s --maxfail=1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } else { exit 0 }
