$ErrorActionPreference = 'Stop'
Set-Location C:\Dev\HybridAITrading

# Optional feature flag to skip upsert (e.g., in CI)
$env:HAT_SKIP_NOTION = $env:HAT_SKIP_NOTION
if ($env:HAT_SKIP_NOTION -eq '1') { Write-Host "Skipping Notion upsert (HAT_SKIP_NOTION=1)"; exit 0 }

$tok = [Environment]::GetEnvironmentVariable('NOTION_TOKEN','Machine')
if (-not $tok) { Write-Host "NOTION_TOKEN (Machine) not set; skipping upsert." -ForegroundColor Yellow; exit 0 }
Import-Module NotionTrader -ErrorAction Stop
$env:NOTION_TOKEN = $tok

$patternDir = 'data\patterns'
$latest = Get-ChildItem $patternDir -Filter 'candidates_*.json' -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $latest) { Write-Host "No candidates_* files in $patternDir. Run Export-PatternCandidates.ps1 first." -ForegroundColor Yellow; exit 0 }
$cand = $latest.FullName
Write-Host "Using candidates file: $cand" -ForegroundColor Cyan

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
