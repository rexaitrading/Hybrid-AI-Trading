param([switch]$Unset = $false)
if ($Unset) {
  Remove-Item Env:STOP_PAPER_LOOP -ErrorAction SilentlyContinue
  "Unset STOP_PAPER_LOOP"
} else {
  $env:STOP_PAPER_LOOP = "1"
  "Set STOP_PAPER_LOOP=1 (loop will exit after next iteration)"
}
