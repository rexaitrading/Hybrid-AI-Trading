param(
  [switch]$ToNotion,
  [int]$Batch = 20,
  [string]$ScriptRoot = "",
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$Rest
)

$ErrorActionPreference = 'Stop'

function Get-PythonPath {
  $venv = 'C:\Dev\HybridAITrading\.venv\Scripts\python.exe'
  if (Test-Path $venv) { return $venv }
  $cmd = Get-Command python, py -EA SilentlyContinue | Select-Object -First 1
  if (-not $cmd) { throw "No Python found. Install Python or activate your venv." }
  return $cmd.Source
}

function Send-NotionBullets {
  param([Parameter(Mandatory=$true)][string[]]$Lines)
  if (-not $env:NOTION_TOKEN -or -not $env:NOTION_PAGE) {
    Write-Warning "NOTION_TOKEN or NOTION_PAGE not set; skipping Notion push."
    return
  }
  $children = @()
  foreach ($ln in $Lines) {
    $children += @{
      "object" = "block"
      "type"   = "bulleted_list_item"
      "bulleted_list_item" = @{
        "rich_text" = @(@{
          "type" = "text"
          "text" = @{ "content" = $ln.Substring(0, [Math]::Min(1900, $ln.Length)) }
        })
      }
    }
  }
  $uri = "https://api.notion.com/v1/blocks/$($env:NOTION_PAGE)/children"
  $headers = @{
    "Authorization"  = "Bearer $($env:NOTION_TOKEN)"
    "Notion-Version" = "2022-06-28"
    "Content-Type"   = "application/json"
  }
  $body = @{ "children" = $children } | ConvertTo-Json -Depth 6
  try {
    Invoke-RestMethod -Method PATCH -Uri $uri -Headers $headers -Body $body | Out-Null
    Write-Host ("Notion updated ({0} bullets)" -f $Lines.Count)
  } catch {
    Write-Warning ("Notion push failed: {0}" -f $_.Exception.Message)
  }
}

# Resolve script folder
$root = $ScriptRoot
if (-not $root) {
  if ($PSScriptRoot) { $root = $PSScriptRoot }
  elseif ($PSCommandPath) { try { $root = Split-Path -Parent $PSCommandPath -ErrorAction Stop } catch {} }
  if (-not $root) {
    if (Test-Path 'C:\Dev\HybridAITrading\scripts\get_news.py') {
      $root = 'C:\Dev\HybridAITrading\scripts'
    } elseif (Test-Path (Join-Path (Get-Location).Path 'get_news.py')) {
      $root = (Get-Location).Path
    } else {
      throw "Cannot resolve script folder. Pass -ScriptRoot 'C:\Dev\HybridAITrading\scripts'."
    }
  }
}

$py     = Get-PythonPath
$script = Join-Path $root 'get_news.py'
if (-not (Test-Path $script)) { throw "Missing get_news.py at $script" }

# ONLY forward what we captured in -Rest
$Passthru = $Rest

if ($ToNotion) {
  $tmp = New-TemporaryFile
  & $py $script --json @Passthru | Tee-Object -FilePath $tmp.FullName | Out-Host
  $lines = Get-Content $tmp.FullName | ForEach-Object {
    try {
      $o = $_ | ConvertFrom-Json
      $t = if ($o.time) { $o.time } else { $o.ts }
      "[{0}] {1} - {2} ({3})" -f $t, $o.symbol, $o.headline, $o.provider
    } catch { $null }
  } | Where-Object { $_ }
  if ($lines.Count -gt 0) {
    $chunk = @()
    foreach ($ln in $lines) {
      $chunk += $ln
      if ($chunk.Count -ge $Batch) { Send-NotionBullets -Lines $chunk; $chunk = @() }
    }
    if ($chunk.Count -gt 0) { Send-NotionBullets -Lines $chunk }
  } else {
    Write-Host "No headlines in this window."
  }
} else {
  & $py $script @Passthru
}