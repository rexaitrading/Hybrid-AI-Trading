param(
  [string] $Path = ".",
  [string] $OutCsv = ".\bom_report.csv",
  [string[]] $ExcludeDirs = @('.git','.gitignore','.venv','node_modules','dist','build','bin','obj','__pycache__','.pytest_cache','.mypy_cache','.ruff_cache','.vscode','.idea','logs','.tox'),
  [switch] $Fix = $false,
  [switch] $IncludeUtf16 = $false
)
$ErrorActionPreference='Stop'; Set-StrictMode -Version Latest
$TextExt = @('.ps1','.psm1','.psd1','.py','.pyw','.ps','.ps1xml','.json','.yml','.yaml','.md','.txt','.csv','.toml','.cfg','.ini','.xml','.html','.htm','.css','.js','.ts','.sql')
$results = New-Object System.Collections.Generic.List[Object]
function Get-BomType([string]$File) {
  try {
    $fs=[IO.File]::OpenRead($File)
    try {
      $buf=New-Object byte[] 4
      $read=$fs.Read($buf,0,4)
      if($read -ge 3 -and $buf[0]-eq0xEF -and $buf[1]-eq0xBB -and $buf[2]-eq0xBF){return 'UTF8-BOM'}
      if($read -ge 2 -and $buf[0]-eq0xFF -and $buf[1]-eq0xFE){return 'UTF16-LE-BOM'}
      if($read -ge 2 -and $buf[0]-eq0xFE -and $buf[1]-eq0xFF){return 'UTF16-BE-BOM'}
      return 'None'
    } finally {$fs.Dispose()}
  } catch { return 'Error' }
}
function Remove-Utf8Bom([string]$File){
  $bytes=[IO.File]::ReadAllBytes($File)
  if($bytes.Length -ge 3 -and $bytes[0]-eq0xEF -and $bytes[1]-eq0xBB -and $bytes[2]-eq0xBF){
    $backup="$File.bom.bak"; Copy-Item -LiteralPath $File -Destination $backup -Force
    [IO.File]::WriteAllBytes($File,$bytes[3..($bytes.Length-1)]); return $true }
  return $false
}
function Convert-Utf16ToUtf8([string]$File,[bool]$BigEndian){
  $enc=if($BigEndian){[Text.Encoding]::BigEndianUnicode}else{[Text.Encoding]::Unicode}
  $backup="$File.bom.bak"; Copy-Item -LiteralPath $File -Destination $backup -Force
  $text=[IO.File]::ReadAllText($File,$enc)
  [IO.File]::WriteAllText($File,$text,(New-Object Text.UTF8Encoding($false))); return $true
}
# enumerate with excludes
$all = Get-ChildItem -Path $Path -Recurse -File -ErrorAction SilentlyContinue | Where-Object {
  $rel = $_.FullName.Substring((Resolve-Path $Path).Path.Length).TrimStart('\','/')
  foreach($d in $ExcludeDirs){ if($rel -match "^(\\|/)?$([regex]::Escape($d))(\\|/|$)"){ return $false } }
  return $true
}
$idx=0; $total=$all.Count
foreach($f in $all){
  $idx++; if($idx%200 -eq 0){ Write-Progress -Activity "Scanning BOMs" -Status "$idx / $total" -PercentComplete ([int](100*$idx/$total)) }
  $bom=Get-BomType $f.FullName
  $ext=[IO.Path]::GetExtension($f.Name).ToLower()
  $isText=$TextExt -contains $ext
  $fixed=$false
  if($Fix -and $isText){
    if($bom -eq 'UTF8-BOM'){ $fixed=Remove-Utf8Bom $f.FullName }
    elseif($IncludeUtf16 -and $bom -eq 'UTF16-LE-BOM'){ $fixed=Convert-Utf16ToUtf8 $f.FullName $false }
    elseif($IncludeUtf16 -and $bom -eq 'UTF16-BE-BOM'){ $fixed=Convert-Utf16ToUtf8 $f.FullName $true }
  }
  $results.Add([pscustomobject]@{ Path=$f.FullName; Size=$f.Length; Ext=$ext; TextLike=if($isText){'Yes'}else{'No'}; BOM=$bom; Fixed=if($fixed){'Yes'}else{'No'} })
}
$results | Sort-Object BOM,Path | Export-Csv -NoTypeInformation -Encoding UTF8 -Path $OutCsv
Write-Host "[ok] BOM scan complete -> $OutCsv (files: $total)" -ForegroundColor Green