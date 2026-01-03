[CmdletBinding()]
param([string]$TodayOverride = "")

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-Today {
  if($TodayOverride){ return [DateTime]::ParseExact($TodayOverride, "yyyy-MM-dd", $null) }
  return (Get-Date)
}

# Minimal institutional rule (holiday calendar handled elsewhere):
# - Sat/Sun => previous Friday
# - Else => today
$dt = Get-Today
$dow = [int]$dt.DayOfWeek  # 0=Sun ... 6=Sat

if($dow -eq 6){ $eff = $dt.AddDays(-1) }      # Sat->Fri
elseif($dow -eq 0){ $eff = $dt.AddDays(-2) }  # Sun->Fri
else { $eff = $dt }

$eff.ToString("yyyy-MM-dd")