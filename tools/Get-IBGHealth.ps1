[CmdletBinding()]
param(
  [string]$StatusPath = $env:HAT_IBG_STATUS_PATH,
  [int]$MaxAgeSec = 120
)

$ok = $true
$reasons = New-Object System.Collections.Generic.List[string]

if([string]::IsNullOrWhiteSpace($StatusPath)){
  $ok = $false; $reasons.Add("missing_env:HAT_IBG_STATUS_PATH")
} elseif(-not (Test-Path -LiteralPath $StatusPath)){
  $ok = $false; $reasons.Add("missing_file:" + $StatusPath)
} else {
  try {
    $raw = Get-Content -LiteralPath $StatusPath -Raw -Encoding utf8
    $j = $raw | ConvertFrom-Json
    if(-not $j.portUp){ $ok = $false; $reasons.Add("portUp=false") }

    # timestamp freshness
    try {
      $ts = [datetimeoffset]::Parse(($j.timestamp + ""))
      $age = [int]((([datetimeoffset]::Now) - $ts).TotalSeconds)
      if($age -gt $MaxAgeSec){ $ok = $false; $reasons.Add("stale_status ageSec=$age max=$MaxAgeSec") }
    } catch {
      $ok = $false; $reasons.Add("bad_timestamp")
    }
  } catch {
    $ok = $false; $reasons.Add("json_parse_fail:" + $_.Exception.Message)
  }
}

# Emit a stable object
[pscustomobject]@{
  ok = $ok
  reasons = @($reasons)
  status_path = $StatusPath
}
