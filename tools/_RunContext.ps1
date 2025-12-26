Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-RepoRoot {
  $toolsDir = Split-Path -Parent $PSCommandPath
  return (Split-Path -Parent $toolsDir)
}

function Get-TodayLocal {
  return (Get-Date).ToString("yyyy-MM-dd")
}