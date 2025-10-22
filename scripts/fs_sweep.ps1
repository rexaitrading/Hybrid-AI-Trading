$ErrorActionPreference='Stop'; Set-StrictMode -Version Latest
function Write-Section([string]$t){ $bar=('='*78); Write-Host "`n$bar`n# $t`n$bar" }

$root=(Get-Location).Path
$src =Join-Path $root 'src\hybrid_ai_trading'
$scr =Join-Path $root 'scripts'
$py  = ".\.venv\Scripts\python.exe"; if(-not(Test-Path $py)){ $py="python" }

Write-Section "Repo roots"
"root = $root"
"src  = $src"
"scripts = $scr"
"python = $py"
"PYTHONPATH (will set for smokes) = $src"

Write-Section "Short tree: scripts (depth<=2)"
Get-ChildItem -Recurse $scr -ErrorAction SilentlyContinue |
  Where-Object { $_.PSIsContainer -or $_.FullName.Split([io.path]::DirectorySeparatorChar).Count -le ($scr.Split([io.path]::DirectorySeparatorChar).Count+2) } |
  Select-Object FullName,LastWriteTime,Length | Format-Table -Auto

Write-Section "Short tree: src/hybrid_ai_trading (depth<=3)"
Get-ChildItem -Recurse $src -ErrorAction SilentlyContinue |
  Where-Object { $_.PSIsContainer -or $_.FullName.Split([io.path]::DirectorySeparatorChar).Count -le ($src.Split([io.path]::DirectorySeparatorChar).Count+3) } |
  Select-Object FullName,LastWriteTime,Length | Format-Table -Auto

Write-Section "Top 20 largest files"
Get-ChildItem -Recurse -File $root | Sort-Object Length -Descending | Select-Object -First 20 FullName,Length,LastWriteTime | Format-Table -Auto

Write-Section "Top 30 most recently modified files"
Get-ChildItem -Recurse -File $root | Sort-Object LastWriteTime -Descending | Select-Object -First 30 FullName,LastWriteTime,Length | Format-Table -Auto

Write-Section "Grep: references to route_ib"
$hits = Select-String -Path (Join-Path $src '*\*.py') -Pattern '\broute_ib\b' -SimpleMatch -ErrorAction SilentlyContinue
if($hits){ $hits | Select-Object Path,LineNumber,Line | Format-Table -Auto } else { "No references found." }

Write-Section "Grep: paper_trader key tokens"
$pt=Join-Path $src 'runners\paper_trader.py'
if(Test-Path $pt){
  Select-String -Path $pt -Pattern 'import yaml|risk_mgr|Provider-only fast path|poll_sec' -SimpleMatch -AllMatches -ErrorAction SilentlyContinue |
    Select-Object Pattern,LineNumber,Line | Format-Table -Auto
}else{ "paper_trader.py not found" }

Write-Section "Python import smokes (PYTHONPATH set)"
$env:PYTHONPATH="$src;$env:PYTHONPATH"
$tests=@(
  "print('providers...',end=''); from hybrid_ai_trading.utils.providers import load_providers; print('OK')",
  "print('route_exec...',end=''); from hybrid_ai_trading.execution.route_exec import place_entry; print('OK')",
  "print('risk_live...',end=''); from hybrid_ai_trading.risk.risk_manager_live import LivePriceRiskManager; print('OK')",
  "print('polygon_news...',end=''); from hybrid_ai_trading.data_clients.polygon_news_client import Client; print('OK')"
)
$i=1
foreach($t in $tests){
  Write-Host ('Smoke #{0}:' -f $i)
  $tmp=[IO.Path]::Combine($env:TEMP, ("fs_sweep_{0}.py" -f ([guid]::NewGuid().ToString('N'))))
  [IO.File]::WriteAllText($tmp,$t,[Text.UTF8Encoding]::new($false))
  & $py $tmp; if($LASTEXITCODE -ne 0){"  -> FAIL ($LASTEXITCODE)"} else {"  -> OK"}
  Remove-Item $tmp -ErrorAction SilentlyContinue; $i++
}
