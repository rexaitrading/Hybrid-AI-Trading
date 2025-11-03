$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true
Set-Location 'C:\Dev\HybridAITrading'

# === FORCE MACHINE TOKEN FOR SCHEDULER & INTERACTIVE RUNS ===
# Always read xoxb token from Machine env; do NOT rely on SecretStore here.
$env:SLACK_BOT_TOKEN = [Environment]::GetEnvironmentVariable('SLACK_BOT_TOKEN','Machine')
if (-not ($env:SLACK_BOT_TOKEN -match '^xoxb-' -and $env:SLACK_BOT_TOKEN.Length -ge 20 -and $env:SLACK_BOT_TOKEN -ne 'xoxb-PASTE_REAL_TOKEN')) {
  throw 'Machine SLACK_BOT_TOKEN missing/invalid. Set the real xoxb- at Machine scope and rerun.'
}
# Transcript
$logDir = 'C:\Dev\HybridAITrading\logs'; New-Item -ItemType Directory -Force $logDir | Out-Null
$log = Join-Path $logDir ("PreMarket_" + (Get-Date -Format 'yyyyMMdd_HHmmss') + ".log")
Start-Transcript -Path $log -Append

# Token bootstrap (SecretStore -> Machine env fallback)
try {
  if (-not $env:SLACK_BOT_TOKEN -or $env:SLACK_BOT_TOKEN -notmatch '^xoxb-') {
    $env:SLACK_BOT_TOKEN = Get-Secret -Name 'SLACK_BOT_TOKEN' -AsPlainText -ErrorAction Stop
  }
} catch {
  if (-not $env:SLACK_BOT_TOKEN -or $env:SLACK_BOT_TOKEN -notmatch '^xoxb-') {
    $env:SLACK_BOT_TOKEN = [Environment]::GetEnvironmentVariable('SLACK_BOT_TOKEN','Machine')
  }
}
if ($env:SLACK_BOT_TOKEN -notmatch '^xoxb-') { throw "SLACK_BOT_TOKEN unavailable." }

function Invoke-Slack {
  param([Parameter(Mandatory)][string]$Method,[hashtable]$Body,[int]$MaxRetries=3)
  $uri="https://slack.com/api/$Method"
  $hdr=@{Authorization="Bearer $($env:SLACK_BOT_TOKEN)";'Content-Type'='application/json'}
  $attempt=0
  while ($true) {
    $attempt++
    try {
      $resp = if($Body){ Invoke-RestMethod -Uri $uri -Method Post -Headers $hdr -Body ($Body|ConvertTo-Json -Depth 12) -TimeoutSec 60 }
              else      { Invoke-RestMethod -Uri $uri -Method Post -Headers $hdr -TimeoutSec 60 }
    } catch {
      if ($_.Exception.Response -and $_.Exception.Response.StatusCode.value__ -eq 429 -and $attempt -lt $MaxRetries) {
        $ra = $_.Exception.Response.Headers['Retry-After']; if(-not $ra){$ra=3}; Start-Sleep -Seconds ([int]$ra); continue
      }
      throw
    }
    if ($null -ne $resp.ok -and -not $resp.ok) {
      $err=$resp.error; $meta=$null
      if($resp.PSObject.Properties.Name -contains 'response_metadata'){
        $rm=$resp.response_metadata; if ($rm -and $rm.PSObject.Properties.Name -contains 'messages' -and $rm.messages) { $meta=($rm.messages -join '; ') }
      }
      throw "Slack API error in [$Method]: $err" + ($(if($meta){"  $meta"}))
    }
    return $resp
  }
}

function Find-LatestFile {
  param([Parameter(Mandatory)][string[]]$Patterns,[string]$Root='C:\Dev\HybridAITrading')
  $candidates=@()
  foreach($p in $Patterns){ $candidates += Get-ChildItem -Path $Root -Recurse -File -ErrorAction SilentlyContinue -Include $p }
  $candidates | Sort-Object LastWriteTime -Desc | Select-Object -First 1
}

function Parse-ORB {
  $jsonFile = Find-LatestFile -Patterns @('orb*.json','*orb*results*.json','*smoke*orb*.json','reports\orb*.json')
  if ($jsonFile) {
    try {
      $j = Get-Content $jsonFile.FullName -Raw | ConvertFrom-Json
      $ok   = $j.ok;   if ($null -eq $ok   -and $j.OK)   { $ok   = $j.OK }
      $warn = $j.warn; if ($null -eq $warn -and $j.WARN) { $warn = $j.WARN }
      $err  = $j.err;  if ($null -eq $err  -and $j.ERR)  { $err  = $j.ERR }
      if ($ok -ne $null -and $warn -ne $null -and $err -ne $null) {
        return @{ ok=[int]$ok; warn=[int]$warn; err=[int]$err; src=$jsonFile.FullName }
      }
      if ($j -is [System.Collections.IEnumerable]) {
        $ok  = ($j | Where-Object {$_.status -match '^(ok|pass|success)$'}).Count
        $err = ($j | Where-Object {$_.status -match '^(err|fail|error)$'}).Count
        $warn= ($j | Where-Object {$_.status -match '^warn(ing)?$'}).Count
        return @{ ok=[int]$ok; warn=[int]$warn; err=[int]$err; src=$jsonFile.FullName }
      }
    } catch {}
  }
  $txtFile = Find-LatestFile -Patterns @('*orb*.txt','*smoke*.txt','logs\*orb*.log','logs\*smoke*.log')
  if ($txtFile) {
    $t = Get-Content $txtFile.FullName -Raw
    $ok   = ([regex]::Match($t,'OK[:\s]+(\d+)','IgnoreCase')).Groups[1].Value
    $warn = ([regex]::Match($t,'WARN(?:ING)?[:\s]+(\d+)','IgnoreCase')).Groups[1].Value
    $err  = ([regex]::Match($t,'ERR(?:OR)?[:\s]+(\d+)','IgnoreCase')).Groups[1].Value
    if ($ok -and $err) {
      if (-not $warn) { $warn = 0 }
      return @{ ok=[int]$ok; warn=[int]$warn; err=[int]$err; src=$txtFile.FullName }
    }
  }
  return @{ ok=0; warn=0; err=0; src=$null }
}

function Parse-JUnit {
  $junit = Find-LatestFile -Patterns @('junit*.xml','test-results*.xml','reports\junit*.xml','pytest*.xml')
  if ($junit) {
    try {
      [xml]$x = Get-Content $junit.FullName -Raw
      $tc=0; $fail=0; $err=0; $skip=0

      $suites = @()
      if ($x.testsuite)  { $suites += $x.testsuite }
      if ($x.testsuites) { $suites += $x.testsuites.testsuite }

      foreach($s in $suites){
        $testsVal  = if ($s.tests)    { [int]$s.tests }    else { 0 }
        $failsVal  = if ($s.failures) { [int]$s.failures } else { 0 }
        $errorsVal = if ($s.errors)   { [int]$s.errors }   else { 0 }
        $skipsVal  = if ($s.skipped)  { [int]$s.skipped }  else { 0 }
        $tc   += $testsVal
        $fail += $failsVal
        $err  += $errorsVal
        $skip += $skipsVal
      }

      if ($tc -eq 0 -and $x.SelectNodes('//testcase')) {
        $cases = $x.SelectNodes('//testcase')
        $tc    = $cases.Count
        $fail  = ($x.SelectNodes('//failure')).Count
        $err   = ($x.SelectNodes('//error')).Count
        $skip  = ($x.SelectNodes('//skipped')).Count
      }

      $pass = [int]($tc - $fail - $err - $skip)
      return @{ pass=$pass; fail=([int]($fail+$err)); skip=[int]$skip; total=[int]$tc; src=$junit.FullName }
    } catch {}
  }
  return @{ pass=0; fail=0; skip=0; total=0; src=$null }
}

function Parse-Coverage {
  $cov = Find-LatestFile -Patterns @('coverage.xml','reports\coverage.xml','cov*.xml')
  if ($cov) {
    try {
      [xml]$c = Get-Content $cov.FullName -Raw
      $rate = $c.coverage.'line-rate'
      if ($rate) {
        $pct = [math]::Round([double]$rate*100, 2)
        return @{ pct="$pct%"; src=$cov.FullName }
      }
      $lv = $c.SelectSingleNode('//lines-valid'); $lc = $c.SelectSingleNode('//lines-covered')
      if ($lv -and $lc) {
        $pct = if ([double]$lv.InnerText -gt 0) { [math]::Round(( [double]$lc.InnerText / [double]$lv.InnerText )*100, 2) } else { 0 }
        return @{ pct="$pct%"; src=$cov.FullName }
      }
    } catch {}
  }
  $covTxt = Find-LatestFile -Patterns @('coverage.txt','reports\coverage.txt','*coverage*.txt')
  if ($covTxt) {
    $txt = Get-Content $covTxt.FullName -Raw
    $m = [regex]::Match($txt,'(\d{1,3}\.\d{1,2})\s*%')
    if ($m.Success) { return @{ pct="$($m.Groups[1].Value)%"; src=$covTxt.FullName } }
  }
  return @{ pct='N/A'; src=$null }
}

try {
  $orb = Parse-ORB
  $ci  = Parse-JUnit
  $cov = Parse-Coverage

  $orb_ok   = [int]$orb.ok
  $orb_warn = [int]$orb.warn
  $orb_err  = [int]$orb.err

  $ci_pass  = [int]$ci.pass
  $ci_fail  = [int]$ci.fail
  $ci_skip  = [int]$ci.skip
  $ci_total = [int]$ci.total

  $coverage = $cov.pct
  $focus = if ($ci_fail -gt 0 -or $orb_err -gt 0) {
    "Fix failing modules first (RiskHub/Kelly/Regime), rerun Phase3 CI; enforce guardrails (MDD, daily loss cap, cooldown)."
  } else {
    "Proceed to bar-replay  forward play; journal into Notion; review pattern repeatability; prepare live capital injection plan."
  }

  $chanId = 'C09J0KVQLJY'
  $whenPT = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss') + ' PT'

  $fields = @(
    @{ type='mrkdwn'; text="*ORB*\nOK: *$orb_ok*  WARN: *$orb_warn*  ERR: *$orb_err*" },
    @{ type='mrkdwn'; text="*CI*\nPass: *$ci_pass*  Fail: *$ci_fail*  Skip: *$ci_skip*  Total: *$ci_total*  Coverage: *$coverage*" }
  )

  $prov = @()
  if ($orb.src) { $prov += "ORB: $($orb.src)" }
  if ($ci.src)  { $prov += "JUnit: $($ci.src)" }
  if ($cov.src) { $prov += "Coverage: $($cov.src)" }
  if (-not $prov.Count) { $prov += "Sources: (none found; using defaults)" }

  $blocks = @(
    @{ type='header'; text=@{ type='plain_text'; text='Pre-Market ORB / CI Status' } }
    @{ type='section'; fields=$fields }
    @{ type='section'; text=@{ type='mrkdwn'; text="*Focus*: $focus" } }
    @{ type='context'; elements=@(
        @{ type='mrkdwn'; text="Posted: $whenPT" },
        @{ type='mrkdwn'; text="Channel: #hybrid_ai_trading_alerts" },
        @{ type='mrkdwn'; text=($prov -join "  ") }
      )
    }
  )

  $post = Invoke-Slack -Method 'chat.postMessage' -Body @{
    channel = $chanId
    text    = "Pre-Market ORB/CI Status"
    blocks  = $blocks
  }
  " ORB/CI status posted ts: $($post.ts)"
}
catch {
  $msg = "Pre-Market status run failed: $($_.Exception.Message)"
  Invoke-Slack -Method 'chat.postMessage' -Body @{
    channel = 'C09J0KVQLJY'
    text    = $msg
    blocks  = @(@{ type='section'; text=@{ type='mrkdwn'; text=":warning: $msg" } })
  }
  throw
}
finally {
  Stop-Transcript
}
# ======================= End =======================
