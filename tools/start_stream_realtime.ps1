$env:IB_HOST="::1"
# start_stream_realtime.ps1
. (Join-Path $PSScriptRoot "stream.ps1")
start-stream -ClientId "3021" -MdType 1
