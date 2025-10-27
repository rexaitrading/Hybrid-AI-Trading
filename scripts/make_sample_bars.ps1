param(
  [string]$OutFile = ".\data\SYNTH_1m.csv",
  [int]$Minutes = 240,
  [double]$Start = 100.0
)
$dt = [DateTime]::SpecifyKind([DateTime]::Parse("2025-01-02T14:30:00Z"), "Utc")
$rows = New-Object System.Collections.Generic.List[string]
$rows.Add("timestamp,open,high,low,close,volume")
$rand = New-Object System.Random
$px = $Start
for ($i=0;$i -lt $Minutes;$i++) {
  $t = $dt.AddMinutes($i)
  $change = ([Math]::Sin($i/15.0)*0.15) + (($rand.NextDouble()-0.5)*0.20)
  $open = [Math]::Round($px,2)
  $close = [Math]::Round($px + $change,2)
  $hi = [Math]::Round([Math]::Max($open,$close) + ($rand.NextDouble()*0.15),2)
  $lo = [Math]::Round([Math]::Min($open,$close) - ($rand.NextDouble()*0.15),2)
  $vol = 80000 + $rand.Next(0,60000)
  $rows.Add(("{0},{1},{2},{3},{4},{5}" -f ($t.ToString("yyyy-MM-ddTHH:mm:ssZ")),$open,$hi,$lo,$close,$vol))
  $px = $close
}
$rows -join "`r`n" | Set-Content -Encoding UTF8 $OutFile
Write-Host "Wrote $OutFile"
