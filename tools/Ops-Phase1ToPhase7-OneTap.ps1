# tools/Ops-Phase1ToPhase7-OneTap.ps1
[CmdletBinding()]
param(
  [ValidateSet("DailyPremarketNVDA","StartNvdaPaperTicks","RunNvdaPaperOps","Status","StopNvdaPaperTicks","WeeklyDeep","MonthlyHygiene")]
  [string]$Mode = "DailyPremarketNVDA",

  # NVDA paper tick producer settings
  [int]$SecondsBetween = 5,
  [int]$Ticks = 720,          # 1 hour if SecondsBetween=5
  [int]$NPerTick = 20,
  [int]$MinEvents = 25
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

function Fail([string]$m){
  Write-Host ("[OPS-7] FAIL-CLOSED: " + $m) -ForegroundColor Red
  exit 2
}
function Step([string]$name,[scriptblock]$sb){
  Write-Host "`n====================" -ForegroundColor DarkGray
  Write-Host ("STEP: " + $name) -ForegroundColor Cyan
  Write-Host "====================" -ForegroundColor DarkGray
  & $sb
}
function Require([string]$p){
  if(-not (Test-Path -LiteralPath $p)){ Fail "Missing required path: $p" }
}

# 0) Anchor repo root deterministically
$repo = (Resolve-Path ".").Path
if(-not (Test-Path -LiteralPath (Join-Path $repo ".git"))){ Fail "NOT IN REPO ROOT: $repo" }
Set-Location -LiteralPath $repo
$env:PYTHONPATH = (Join-Path $repo "src")

# 1) Paper-safe hard defaults (fail-closed live)
$env:HAT_IS_PAPER="1"
$env:HAT_LIVE_DISABLED="1"
Remove-Item Env:HAT_CONFIRM_LIVE -ErrorAction SilentlyContinue

# 2) Python
$py = Join-Path $repo ".venv\Scripts\python.exe"
Require $py

# 3) Core tools
$intelTool      = Join-Path $repo "tools\Run-IntelPipeline.ps1"
$contractPack   = Join-Path $repo "tools\Run-Premarket-ContractPack.ps1"
$blockGCheck    = Join-Path $repo "tools\Invoke-BlockGCheck.ps1"
$nvdaPaperOps   = Join-Path $repo "tools\Run-NvdaPaperOps.ps1"

function Invoke-Tool([string]$label,[string]$file,[string[]]$args=@()){
  Require $file
  & powershell -NoProfile -ExecutionPolicy Bypass -File $file @args *>&1 | Out-Host
  $ec=$LASTEXITCODE
  "EXIT_{0}={1}" -f $label,$ec | Out-Host
  if($ec -ne 0){ Fail "$label failed exit=$ec" }
}

function Assert-BlockGReadyNVDA(){
  Invoke-Tool "BLOCKG" $blockGCheck @("-Symbol","NVDA","-Mode","ALL_STRICT")
}

function Sentiment-Smoke(){
  Step "Sentiment smoke (vader active + gate callable)" {
    & $py -c "from hybrid_ai_trading.risk.sentiment_filter import SentimentFilter; f=SentimentFilter(model='vader'); print('SENTIMENT_VADER_ACTIVE=', f.analyzer is not None)" | Out-Host
    & $py -c "from hybrid_ai_trading.risk.sentiment_gate import score_headlines_for_symbols; out=score_headlines_for_symbols('NVDA', hours_back=48, limit=10, side='BUY'); print('SENTIMENT_TOTAL=', out.get('total'))" | Out-Host
  }
}

function Start-NvdaPaperTicks(){
  Step "Start NVDA paper tick producer loop (foreground)" {
    $runner = Join-Path $repo "src\hybrid_ai_trading\runners\nvda_paperlive_today.py"
    Require $runner

    "[LOOP] ticks=$Ticks every ${SecondsBetween}s nPerTick=$NPerTick" | Out-Host
    for($i=1; $i -le $Ticks; $i++){
      if(($i % [int](60 / [math]::Max(1,$SecondsBetween))) -eq 1){
        & powershell -NoProfile -ExecutionPolicy Bypass -File $blockGCheck -Symbol NVDA *> $null
        if($LASTEXITCODE -ne 0){ Fail "BlockG not ready during loop; stopping" }
      }

      $ts = Get-Date -Format "yyyyMMdd_HHmmss"
      $out = Join-Path $repo ("logs\nvda_paperlive_tick_{0}.jsonl" -f $ts)

      & $py -u $runner --out $out --n $NPerTick --edge 0.03 --micro 0.60 --pnl-samples 1 *>&1 | Out-Host
      Start-Sleep -Seconds $SecondsBetween
    }
  }
}

function Stop-NvdaPaperTicks(){
  Write-Host "[OPS-7] Tick loop is foreground. Use Ctrl+C to stop the running loop." -ForegroundColor Yellow
}

function Status(){
  Step "Status snapshot" {
    "REPO=$repo" | Out-Host
    "PYTHONPATH=$env:PYTHONPATH" | Out-Host
    "HAT_IS_PAPER=$env:HAT_IS_PAPER  HAT_LIVE_DISABLED=$env:HAT_LIVE_DISABLED" | Out-Host

    & powershell -NoProfile -ExecutionPolicy Bypass -File $blockGCheck -Symbol NVDA *>&1 | Out-Host
    "EXIT_BLOCKG=$LASTEXITCODE" | Out-Host

    Get-ChildItem -File .\logs -ErrorAction SilentlyContinue |
      Where-Object { $_.Name -match '^nvda_paperlive_tick_\d{8}_\d{6}\.jsonl$' } |
      Sort-Object LastWriteTime -Descending |
      Select-Object -First 3 Name,Length,LastWriteTime |
      Format-Table -AutoSize | Out-Host

    $must=@(".\logs\risk_pulse.jsonl",".\logs\intel_feed.jsonl",".\src\.intel\risk_pulse.jsonl")
    foreach($p in $must){
      if(Test-Path $p){
        $it=Get-Item $p
        "{0} bytes={1} last={2}" -f $p,$it.Length,$it.LastWriteTime | Out-Host
      } else {
        "MISSING: $p" | Out-Host
      }
    }
  }
}

function Daily-PremarketNVDA(){
  Step "Intel pipeline (Phase6 intake -> contract)" { Invoke-Tool "INTEL" $intelTool @() }
  Step "ContractPack (PH23/PH4/GS/EVH/BlockG build+check)" { Invoke-Tool "CONTRACTPACK" $contractPack @("-Symbol","NVDA") }
  Step "Final authority: BlockG checker (NVDA)" { Assert-BlockGReadyNVDA }
  Sentiment-Smoke
  Step "OK: Daily premarket gates GREEN (paper-safe; NVDA)" { "[GO] DAILY PRE-MARKET (paper-safe; NVDA) gates are GREEN." | Out-Host }
}

function Weekly-Deep(){
  Step "Weekly deep validation" {
    git fetch --all --prune
    git status --porcelain | Out-Host
    & $py -m pytest -q
    if($LASTEXITCODE -ne 0){ Fail "pytest failed rc=$LASTEXITCODE" }
    "WEEKLY_OK" | Out-Host
  }
}

function Monthly-Hygiene(){
  Step "Monthly hygiene" {
    git fetch --all --prune
    git status --porcelain | Out-Host
    & $py -m pytest -q
    if($LASTEXITCODE -ne 0){ Fail "pytest failed rc=$LASTEXITCODE" }
    & $py -m pip --version | Out-Host
    & $py -c "import sys; print(sys.version)" | Out-Host
    "MONTHLY_OK" | Out-Host
  }
}

switch($Mode){
  "DailyPremarketNVDA" { Daily-PremarketNVDA; exit 0 }
  "StartNvdaPaperTicks" { Assert-BlockGReadyNVDA; Start-NvdaPaperTicks; exit 0 }
  "RunNvdaPaperOps" { Require $nvdaPaperOps; Invoke-Tool "NVDA_PAPER_OPS" $nvdaPaperOps @("-MinEvents",$MinEvents); exit 0 }
  "Status" { Status; exit 0 }
  "StopNvdaPaperTicks" { Stop-NvdaPaperTicks; exit 0 }
  "WeeklyDeep" { Weekly-Deep; exit 0 }
  "MonthlyHygiene" { Monthly-Hygiene; exit 0 }
  default { Fail "Unknown Mode=$Mode" }
}
