$ErrorActionPreference='Stop'; Set-StrictMode -Version Latest

function Write-Section([string]$t){ $bar=('='*78); Write-Host "`n$bar`n# $t`n$bar" }

$root=(Get-Location).Path
$src =Join-Path $root 'src\hybrid_ai_trading'
$scr =Join-Path $root 'scripts'
$py  = ".\.venv\Scripts\python.exe"; if(-not(Test-Path $py)){ $py="python" }
$report = Join-Path $root "__files_active_tree.txt"

$env:PYTHONPATH="$src;$env:PYTHONPATH"

# Buffer output then write to file at end (also echo to console)
$buf = New-Object System.Text.StringBuilder

function Out-Both([string]$s){
  $null = $buf.AppendLine($s)
  Write-Host $s
}

Out-Both ("root = {0}" -f $root)
Out-Both ("src  = {0}" -f $src)
Out-Both ("python = {0}" -f $py)

Write-Section "Short tree: scripts (depth<=2)"
$items = Get-ChildItem -Recurse $scr -ErrorAction SilentlyContinue |
  Where-Object { $_.PSIsContainer -or $_.FullName.Split([io.path]::DirectorySeparatorChar).Count -le ($scr.Split([io.path]::DirectorySeparatorChar).Count+2) } |
  Select-Object FullName,LastWriteTime,Length
$items | Format-Table -Auto | Out-String | ForEach-Object { Out-Both $_ }

Write-Section "Short tree: src/hybrid_ai_trading (depth<=3)"
$items = Get-ChildItem -Recurse $src -ErrorAction SilentlyContinue |
  Where-Object { $_.PSIsContainer -or $_.FullName.Split([io.path]::DirectorySeparatorChar).Count -le ($src.Split([io.path]::DirectorySeparatorChar).Count+3) } |
  Select-Object FullName,LastWriteTime,Length
$items | Format-Table -Auto | Out-String | ForEach-Object { Out-Both $_ }

Write-Section "Top 20 largest files"
Get-ChildItem -Recurse -File $root |
  Sort-Object Length -Descending |
  Select-Object -First 20 FullName,Length,LastWriteTime |
  Format-Table -Auto | Out-String | ForEach-Object { Out-Both $_ }

Write-Section "Top 30 most recently modified files"
Get-ChildItem -Recurse -File $root |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 30 FullName,LastWriteTime,Length |
  Format-Table -Auto | Out-String | ForEach-Object { Out-Both $_ }

Write-Section "Grep: hotspots"
$patterns = @(
  'route_ib',
  'ExecRouter',
  'cfg\["risk_mgr"\]\s*=\s*rm',
  '\bpoll_sec\b'
)
foreach($pat in $patterns){
  Out-Both ("-- pattern: {0}" -f $pat)
  $hits = Select-String -Path (Join-Path $src '*\*.py') -Pattern $pat -ErrorAction SilentlyContinue
  if($hits){
    ($hits | Select-Object Path,LineNumber,Line | Format-Table -Auto | Out-String) | ForEach-Object { Out-Both $_ }
  } else {
    Out-Both "  (no matches)"
  }
}

Write-Section "Python import smokes"
$tests=@(
  "print('providers...',end=''); from hybrid_ai_trading.utils.providers import load_providers; print('OK')",
  "print('route_exec...',end=''); from hybrid_ai_trading.execution.route_exec import place_entry; print('OK')",
  "print('broker_api...',end=''); import hybrid_ai_trading.execution.broker_api as B; print(hasattr(B,'place_limit'))",
  "print('risk_live...',end=''); from hybrid_ai_trading.risk.risk_manager_live import LivePriceRiskManager; print('OK')"
)
$i=1
foreach($t in $tests){
  Write-Host ('Smoke #{0}:' -f $i)
  $tmp=[IO.Path]::Combine($env:TEMP, ("tree_smoke_{0}.py" -f ([guid]::NewGuid().ToString('N'))))
  [IO.File]::WriteAllText($tmp,$t,[Text.UTF8Encoding]::new($false))
  & $py $tmp
  if($LASTEXITCODE -ne 0){ Out-Both ("  -> FAIL ({0})" -f $LASTEXITCODE) } else { Out-Both "  -> OK" }
  Remove-Item $tmp -ErrorAction SilentlyContinue
  $i++
}

# Write combined report
[IO.File]::WriteAllText($report, $buf.ToString(), [Text.UTF8Encoding]::new($false))
Out-Both ("`nSaved snapshot: {0}" -f $report)
