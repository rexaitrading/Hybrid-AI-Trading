function Update-NotionRForPage {
  param([Parameter(Mandatory)][string]$PageUrlOrId)

  if (-not $env:NOTION_TOKEN) { throw "NOTION_TOKEN not set." }
  $hdr=@{'Authorization'="Bearer $env:NOTION_TOKEN";'Notion-Version'='2022-06-28';'Content-Type'='application/json'}

  function _toId([string]$s){
    if($s -match '([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})'){ return $matches[1].ToLower() }
    if($s -match '([0-9a-fA-F]{32})'){ $r=$matches[1].ToLower(); return ('{0}-{1}-{2}-{3}-{4}' -f $r.Substring(0,8),$r.Substring(8,4),$r.Substring(12,4),$r.Substring(16,4),$r.Substring(20,12)) }
    throw "No UUID in: $s"
  }

  $pageId=_toId $PageUrlOrId
  $p=Invoke-RestMethod -Method GET -Headers $hdr -Uri ("https://api.notion.com/v1/pages/{0}" -f $pageId)

  $risk = if($p.properties.risk_usd.number -ne $null){ [double]$p.properties.risk_usd.number } else { 0.0 }
  $net  = if($p.properties.net_pnl.formula.number -ne $null){ [double]$p.properties.net_pnl.formula.number }
          elseif($p.properties.net_pnl.number -ne $null){ [double]$p.properties.net_pnl.number } else { 0.0 }
  $R    = if($risk -gt 0){ [math]::Round(($net/$risk),6) } else { 0.0 }

  $body=@{properties=@{ r_multiple=@{ number=$R } }} | ConvertTo-Json -Depth 10
  Invoke-RestMethod -Method PATCH -Headers $hdr -Uri ("https://api.notion.com/v1/pages/{0}" -f $pageId) -Body $body | Out-Null

  $name = if($p.properties.Name.title){ ($p.properties.Name.title|%{$_.plain_text}) -join '' } else { '' }
  Write-Host ("Updated {0}  name='{1}'  net_pnl={2}  risk_usd={3}  r_multiple={4}" -f $pageId,$name,$net,$risk,$R) -ForegroundColor Green
}
