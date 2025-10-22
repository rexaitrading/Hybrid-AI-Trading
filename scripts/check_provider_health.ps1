param(
  [string]$Url = "http://127.0.0.1:8789/health/providers",
  [string]$Log = ".\.logs\provider_health.log"
)
$ErrorActionPreference = "Stop"
$stamp = (Get-Date).ToString("s")
$stage = "init"
try {
  # --- mkdir (pure .NET) ---
  $stage = "mkdir"
  $logPath = [System.IO.Path]::GetFullPath($Log)
  $dir     = [System.IO.Path]::GetDirectoryName($logPath)
  if ([string]::IsNullOrWhiteSpace($dir)) { $dir = (Join-Path (Get-Location).Path ".logs") }
  [System.IO.Directory]::CreateDirectory($dir) | Out-Null

  # --- http (HttpClient, no param-set issues) ---
  $stage = "http"
  $client = [System.Net.Http.HttpClient]::new()
  $client.Timeout = [TimeSpan]::FromSeconds(10)
  $jsonText = $client.GetStringAsync($Url).GetAwaiter().GetResult()

  # --- parse ---
  $stage = "parse"
  $json = $jsonText | ConvertFrom-Json

  # --- format ---
  $stage = "format"
  $okCount = ($json.checks | Where-Object { $_.ok -eq $true }).Count
  $tot     = ($json.checks).Count

  $arr = New-Object System.Collections.Generic.List[string]
  foreach ($c in $json.checks) {
    $state = if ($c.ok) {'OK'} else {'BAD'}
    [void]$arr.Add(("{0}:{1}ms:{2}" -f $c.provider, $c.lat_ms, $state))
  }
  $line = "[$stamp] ok=$okCount/$tot  " + ($arr.ToArray() -join '  ')

  # --- write (pure .NET, UTF8 no BOM) ---
  $stage = "write"
  $utf8 = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::AppendAllText($logPath, $line + [Environment]::NewLine, $utf8)

  # echo to console too
  Write-Host $line
}
catch {
  $err = "[$stamp] ERROR(stage=$stage): $($_.Exception.Message)"
  $utf8 = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::AppendAllText(([System.IO.Path]::GetFullPath($Log)), $err + [Environment]::NewLine, $utf8)
  Write-Host $err
}
