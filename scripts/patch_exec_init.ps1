$ErrorActionPreference='Stop'; Set-StrictMode -Version Latest
$init = Join-Path (Join-Path (Get-Location).Path 'src\hybrid_ai_trading\execution') '__init__.py'
if(-not (Test-Path $init)){ throw "Missing execution/__init__.py: $init" }
$txt = Get-Content -Raw -LiteralPath $init

# Remove or guard any direct import of route_ib
$orig=$txt
$txt = $txt -replace '(?m)^\s*from\s+\.\s*route_ib\s+import\s+.*$', '# (patched) route_ib disabled; using route_exec only'

# Ensure route_exec import exists (idempotent)
if($txt -notmatch '(?m)^\s*from\s+\.\s*route_exec\s+import\s+.*$'){
  $txt = "from .route_exec import *  # patched to prefer route_exec`r`n" + $txt
}

if($txt -ne $orig){
  [IO.File]::WriteAllText($init, $txt, [Text.UTF8Encoding]::new($false))
  "Patched execution/__init__.py -> prefer route_exec; route_ib disabled."
}else{
  "execution/__init__.py already has route_exec-only semantics; no change."
}
