param(
  [string]$RepoRoot = 'C:\Dev\HybridAITrading',
  [string]$RelPath  = 'src\hybrid_ai_trading\trade_engine.py',
  [int]   $HugeBytes = 1572864  # 1.5 MB safeguard
)

$ErrorActionPreference = 'Stop'

function Write-Info($m){ Write-Host "[INFO] $m" -ForegroundColor Cyan }
function Write-Ok  ($m){ Write-Host "[OK]   $m" -ForegroundColor Green }
function Fail      ($m){ Write-Host "[ERR]  $m" -ForegroundColor Red; exit 2 }
function LeadingSpaces([string]$s){ $m=[regex]::Match($s,'^( +)'); if($m.Success){$m.Groups[1].Value.Length}else{0} }

# Resolve paths
$target = Join-Path $RepoRoot $RelPath
if (!(Test-Path $target)) { Fail "Not found: $target" }

# 0) Backup & quarantine if huge/corrupt
New-Item -ItemType Directory -Force (Join-Path $RepoRoot '.backup') | Out-Null
$bak = Join-Path $RepoRoot ".backup\trade_engine.py.$(Get-Date -Format 'yyyyMMdd_HHmmss').bak"
Copy-Item $target $bak -Force
Write-Info "Backup -> $bak"

$fi = Get-Item $target
$needQuarantine = $false
try {
  $hasClass = Select-String -Path $target -Pattern '^\s*class\s+TradeEngine\b' -Quiet
  if (-not $hasClass) { $needQuarantine = $true }
  if ($fi.Length -gt $HugeBytes) { $needQuarantine = $true }
} catch { $needQuarantine = $true }

if ($needQuarantine) {
  $qdir = Join-Path $RepoRoot '.quarantine'
  New-Item -ItemType Directory -Force $qdir | Out-Null
  $qpath = Join-Path $qdir ("trade_engine.py.{0}.corrupt" -f (Get-Date -Format 'yyyyMMdd_HHmmss'))
  Copy-Item $target $qpath -Force
  Write-Warning "Quarantined current file -> $qpath (len=$($fi.Length))"

  $cand = Get-ChildItem (Join-Path $RepoRoot '.backup') -Filter 'trade_engine.py.*.bak' |
          Sort-Object LastWriteTime -Descending |
          Where-Object {
            $_.Length -le $HugeBytes -and
            (Select-String -Path $_.FullName -Pattern '^\s*class\s+TradeEngine\b' -Quiet)
          } | Select-Object -First 1

  if (-not $cand) { Fail "No sane backup to restore. Use git to restore $target." }

  Copy-Item $cand.FullName $target -Force
  Write-Info "Restored from backup: $($cand.FullName) (len=$($cand.Length))"
}

# 1) Load & normalize (stream-safe)
$lines = Get-Content $target -Encoding UTF8
$lines = $lines | ForEach-Object { ($_ -replace "`t","    ") -replace '\s+$','' }

# 2) Ensure required imports
$needsOs     = -not ($lines | Select-String -Pattern '^\s*import\s+os\b')
$needsTyping = -not ($lines | Select-String -Pattern '^\s*from\s+typing\s+import\s+Dict,\s*Any\b|\bDict\[\s*str\s*,\s*Any\s*\]')
if ($needsOs -or $needsTyping) {
  $insIdx = 0
  for ($i=0; $i -lt $lines.Count; $i++){
    if ($lines[$i] -match '^\s*(#\!|#\s*-\*-)|^\s*$'){ continue } else { $insIdx = $i; break }
  }
  $block = @()
  if ($needsOs)     { $block += 'import os' }
  if ($needsTyping) { $block += 'from typing import Dict, Any' }
  $before = @(); if ($insIdx -gt 0) { $before = $lines[0..($insIdx-1)] }
  $after  = $lines[$insIdx..($lines.Count-1)]
  $lines  = @($before + $block + @('') + $after)
  Write-Info "Added imports: $($block -join ', ')"
}

# 3) Inject alert() into class TradeEngine if missing
$hasAlert = ($lines | Select-String -Pattern '^\s*def\s+alert\s*\(')
if (-not $hasAlert) {
  $cls = $lines | Select-String -Pattern '^\s*class\s+TradeEngine\b' | Select-Object -First 1
  if (-not $cls) { Fail "class TradeEngine not found (after restoration)." }
  $clsIdx = $cls.LineNumber - 1

  $clsIndent    = LeadingSpaces $lines[$clsIdx]
  $methodIndent = $clsIndent + 4
  $indent       = ' ' * $methodIndent
  $indentBody   = ' ' * ($methodIndent + 4)

  # insertion point (after optional class docstring)
  $ins = $clsIdx + 1
  while ($ins -lt $lines.Count -and $lines[$ins].Trim().Length -eq 0) { $ins++ }
  if ($ins -lt $lines.Count -and $lines[$ins].TrimStart() -match '^("""|\'\'\')') {
    $q = $matches[1]; $ins++
    while ($ins -lt $lines.Count -and ($lines[$ins] -notmatch "$q")) { $ins++ }
    if ($ins -lt $lines.Count) { $ins++ }
    while ($ins -lt $lines.Count -and $lines[$ins].Trim().Length -eq 0) { $ins++ }
  }

  $method = @(
    "$indent" + "def alert(self, message: str) -> Dict[str, Any]:"
    "$indentBody" + '"""Minimal alert shim with deterministic branches for tests.'
    "$indentBody" + ''
    "$indentBody" + 'Branches:'
    "$indentBody" + '  - If env TRADE_ALERT_MODE is missing => "noenv"'
    "$indentBody" + '  - If TRADE_ALERT_MODE == "fail"     => simulated failure'
    "$indentBody" + '  - Otherwise                          => success path'
    "$indentBody" + 'Stores last result in self.last_alert for inspection.'
    "$indentBody" + '"""'
    "$indentBody" + 'mode = os.getenv("TRADE_ALERT_MODE")'
    "$indentBody" + 'if not mode:'
    "$indentBody" + '    self.last_alert = {"ok": False, "status": "noenv", "message": message}'
    "$indentBody" + '    return self.last_alert'
    "$indentBody" + 'if str(mode).lower() == "fail":'
    "$indentBody" + '    self.last_alert = {"ok": False, "status": "fail", "message": message}'
    "$indentBody" + '    return self.last_alert'
    "$indentBody" + 'try:'
    "$indentBody" + '    print(f"[ALERT] {message}")'
    "$indentBody" + 'except Exception:'
    "$indentBody" + '    pass'
    "$indentBody" + 'self.last_alert = {"ok": True, "status": "sent", "message": message}'
    "$indentBody" + 'return self.last_alert'
    ""
  )

  $before = $lines[0..($ins-1)]
  $after  = $lines[$ins..($lines.Count-1)]
  $lines  = @($before + $method + $after)
  Write-Ok "Injected TradeEngine.alert() minimal shim."
} else {
  Write-Info "alert() already present  no injection needed."
}

# 4) Final hygiene & save (UTF-8 no BOM, LF)
$lines = $lines | ForEach-Object { ($_ -replace "`t","    ") -replace '\s+$','' }
$utf8 = New-Object System.Text.UTF8Encoding($false)
[IO.File]::WriteAllText($target, ($lines -join "`n") + "`n", $utf8)
Write-Ok "Normalized file to UTF-8 no BOM + LF."
Write-Ok "Patch complete: $target"
exit 0
