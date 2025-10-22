param([string]$JobName = "PaperLoop")
$ErrorActionPreference = 'Stop'
$j = Get-Job -Name $JobName -ErrorAction SilentlyContinue
if (-not $j) { "No job named $JobName"; exit 0 }
try { Stop-Job -Job $j -ErrorAction SilentlyContinue } catch {}
try { Remove-Job -Job $j -Force -ErrorAction SilentlyContinue } catch {}
"Stopped & removed job: $JobName"
