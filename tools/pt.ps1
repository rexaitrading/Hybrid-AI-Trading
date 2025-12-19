[CmdletBinding()]
param(
  [Parameter(ValueFromRemainingArguments=$true)]
  [string[]]$Args
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Usage examples:
#   .\tools\pt.ps1 -q tests/config/test_settings.py::test_get_config_value
#   .\tools\pt.ps1 -q tests/execution/test_algos_wrapper.py -q
#   .\tools\pt.ps1 -q --collect-only

& pytest @Args
exit $LASTEXITCODE