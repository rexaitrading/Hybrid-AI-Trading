# NotionTrader

Multi-source Notion journaling helpers for HybridAITrading.

## Exported functions
- `New-NotionPageMultiSource`
- `Write-TradeJournalEntry`

## Usage
```powershell
Import-Module NotionTrader
($res = Write-TradeJournalEntry -Title 'Test' -Symbol 'AAPL' -Side 'BUY' -Qty 1).url
```

**Requires**
- ``$env:NOTION_TOKEN`` set (internal `ntn_` token)
- Request header `Notion-Version: 2025-09-03`
