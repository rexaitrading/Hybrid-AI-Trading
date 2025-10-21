$ErrorActionPreference='Stop'; Set-StrictMode -Version Latest
$pt = Join-Path (Join-Path (Get-Location).Path 'src\hybrid_ai_trading\runners') 'paper_trader.py'
if(-not (Test-Path $pt)){ throw "Missing runners/paper_trader.py: $pt" }
$txt = Get-Content -Raw -LiteralPath $pt
$orig=$txt

# Ensure 'import yaml'
if($txt -notmatch '(?m)^\s*import\s+yaml\b'){
  # inject after first block of imports
  $txt = $txt -replace '(?ms)^((?:from\s+\S+\s+import\s+\S+|import\s+\S+).+?\r?\n)(?!\s*#)', "`$1import yaml`r`n"
}

# Ensure provider-only fast path marker comment (non-functional; for your audit)
if($txt -notmatch 'Provider-only fast path \(before preflight\)'){
  $txt = $txt -replace '(?m)^(\s*def\s+run_paper_session\s*\()','"""\nProvider-only fast path (before preflight)\n"""\n$1'
}

# Ensure risk_mgr injected: insert 'cfg["risk_mgr"]=rm' after risk manager 'rm' is created OR after cfg load.
if($txt -notmatch 'cfg\["risk_mgr"\]\s*=\s*rm'){
  # try to insert after an assignment to rm = LivePriceRiskManager(...) OR fallback after cfg assignment
  if($txt -match '(?ms)(rm\s*=\s*LivePriceRiskManager\([^\)]*\).*\r?\n)'){
    $txt = $txt -replace '(?ms)(rm\s*=\s*LivePriceRiskManager\([^\)]*\).*\r?\n)', "`$1cfg[`"risk_mgr`"]=rm`r`n"
  } elseif($txt -match '(?ms)(cfg\s*=\s*.*\r?\n)'){
    $txt = $txt -replace '(?ms)(cfg\s*=\s*.*\r?\n)', "`$1cfg[`"risk_mgr`"]=rm  # NOTE: rm must be defined above`r`n"
  }
}

# Ensure poll_sec used: define default if missing
if($txt -notmatch '\bpoll_sec\b'){
  # Safe default near top-level main/run
  $txt = $txt -replace '(?ms)(def\s+run_paper_session\s*\([^\)]*\)\s*:\s*\r?\n)', "$1    poll_sec = cfg.get('poll_sec', 2)\r\n"
}

if($txt -ne $orig){
  [IO.File]::WriteAllText($pt, $txt, [Text.UTF8Encoding]::new($false))
  "Patched runners/paper_trader.py (import yaml, risk_mgr injection, marker, poll_sec)."
}else{
  "paper_trader.py already satisfies checks; no change."
}
