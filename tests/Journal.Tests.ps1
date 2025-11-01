#requires -Version 5.1
Set-StrictMode -Version Latest

$repoRoot        = Split-Path -Parent $PSScriptRoot
$scriptUnderTest = Join-Path $repoRoot 'scripts\journal\Write-Trade.ps1'

if (Get-Module NotionTrader) { Remove-Module NotionTrader -Force }
if (-not (Test-Path $scriptUnderTest)) { throw "SUT missing: $scriptUnderTest" }

. $scriptUnderTest

Describe 'Write-TradeJournalEntry (Notion 2025-09-03, data source parent)' {

  BeforeEach {
    $env:NOTION_TOKEN = 'secret_dummy'
    $DbId         = '2970bf31-ef15-80a6-983e-cf2c836cf97c'
    $DataSourceId = '2970bf31-ef15-809e-802a-000b4911c1fc'
    $SessionId    = 'SMK-20991231'
    $script:CapturedIRM = New-Object System.Collections.Generic.List[object]

    # Catch-all mock to prevent any real HTTP and capture bodies
    Mock Invoke-RestMethod -ParameterFilter { $true } -MockWith {
      $script:CapturedIRM.Add([pscustomobject]@{
        Method=$Method; Uri=$Uri; Headers=$Headers; Body=$Body; ContentType=$ContentType
      }) | Out-Null
      switch ($Method) {
        'Get'   { [pscustomobject]@{ data_sources = @([pscustomobject]@{ id=$DataSourceId; name='Trading Journal'; type='notion' }) } }
        'Post'  { [pscustomobject]@{ object='page'; id='page-1'; url='https://dummy/page-1' } }
        'Patch' { [pscustomobject]@{} }
        default { [pscustomobject]@{} }
      }
    } -Verifiable
  }

  It 'creates page with parent.data_source_id when -DataSourceId is passed' {
    $res = Write-TradeJournalEntry -DataSourceId $DataSourceId -Title 'Smoke OK (pester)' -Symbol 'SPY' -Side 'BUY' -Status 'Open' -EntryPx 500 -Qty 1

    $posts = @($script:CapturedIRM | Where-Object { $_.Method -eq 'Post' })
    $posts.Count | Should -Be 1

    $obj = $posts[-1].Body | ConvertFrom-Json
    $obj.parent.PSObject.Properties.Name | Should -Contain 'data_source_id'
    $obj.parent.data_source_id          | Should -Be $DataSourceId
    $obj.properties.symbol.rich_text[0].text.content | Should -Be 'SPY'
    $obj.properties.side.select.name                 | Should -Be 'BUY'
    $obj.properties.status.select.name               | Should -Be 'Open'
    $res | Should -Not -BeNullOrEmpty
  }

  It 'PATCHes session_id when -SessionId is provided' {
    $null = Write-TradeJournalEntry -DataSourceId $DataSourceId -Title 'Smoke OK (pester patch)' -Symbol 'SPY' -Side 'BUY' -Status 'Open' -EntryPx 500 -Qty 1 -SessionId $SessionId

    $patches = @($script:CapturedIRM | Where-Object { $_.Method -eq 'Patch' })
    $patches.Count | Should -Be 1
    ($patches[-1].Body -match '"session_id"') | Should -BeTrue
  }
AfterEach { }
}
