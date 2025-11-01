$ErrorActionPreference = 'Stop'
Set-Location C:\Dev\HybridAITrading
$tok = [Environment]::GetEnvironmentVariable('NOTION_TOKEN','Machine')
if (-not $tok) { throw 'NOTION_TOKEN (Machine) not set; skipping upsert.' }
Import-Module NotionTrader -ErrorAction Stop
$env:NOTION_TOKEN = $tok
$day  = Get-Date -Format 'yyyyMMdd'
$cand = Join-Path 'data\patterns' "candidates_$day.json"
if (-not (Test-Path $cand)) { throw "Candidates not found: $cand. Run Export-PatternCandidates.ps1 first." }
$list = Get-Content -Raw $cand | ConvertFrom-Json
foreach($p in $list){
  $props = @{
    ts            = @{ date = @{ start = $p.ts } }
    context_notes = @{ rich_text = @(@{ text = @{ content = $p.notes }}) }
    confidence    = @{ number = [double]$p.confidence }
    regime_conf   = @{ number = [double]$p.regime_conf }
  }
  if ($p.context_tags) { $props.context_tags = @{ multi_select = @() }; foreach($t in $p.context_tags){ $props.context_tags.multi_select += @{ name = "$t" } } }
  if ($p.setup)        { $props.setup       = @{ select = @{ name = $p.setup } } }
  $r = New-NotionPageMultiSource -DbId '2970bf31ef1580a6983ecf2c836cf97c' -DataSourceName 'Edge Feed' -Title $p.name -ExtraProperties $props
  "UPSERT -> $($p.name) : $($r.url)"
}
