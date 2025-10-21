param([string]$JobName = "PaperLoop")
$j = Get-Job -Name $JobName -ErrorAction SilentlyContinue
if ($j) { $j | Format-List Id,Name,State,HasMoreData } else { "No job named $JobName" }
