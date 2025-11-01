# Journal.LoopFix.Tests.ps1  minimal smoke that matches current function signature
# Your function parameters: DataSourceName, DbId, Title, Symbol, Side, Status, EntryPx, Qty, etc.

Set-StrictMode -Version Latest

Describe "Write-TradeJournalEntry (LoopFix, by DataSourceName)" {

    BeforeAll {
        # Make sure the module is loaded (adjust if your test harness loads differently)
        if (-not (Get-Module NotionTrader)) {
            Import-Module NotionTrader -ErrorAction Stop
        }

        # Provide a DataSourceName; fall back to env or a literal
        if (-not (Get-Variable -Name DataSourceName -Scope Script -ErrorAction SilentlyContinue)) {
            $script:DataSourceName = if ($env:NOTION_SOURCE_NAME) { $env:NOTION_SOURCE_NAME } else { 'LoopFix Source' }
        }

        # Capture IRM calls without relying on internal arrays that may mutate
        $script:Calls = New-Object System.Collections.Generic.List[object]

        # Mock IRM to capture all calls. Keep defaults so only Write-TradeJournalEntry uses it.
        Mock -ModuleName NotionTrader -CommandName Invoke-RestMethod -MockWith {
            $script:Calls.Add([pscustomobject]@{
                Method = $Method
                Uri    = $Uri
                Body   = $Body
            })
            # Return a plausible page stub
            @{ id = 'dummy-page-id' }
        } -Verifiable
    }

    It "creates a page via POST to /v1/pages using DataSourceName" {
        # Call with parameters that exist on the real command
        $cmd = Get-Command Write-TradeJournalEntry -Module NotionTrader -ErrorAction Stop

        $null = & $cmd `
            -DataSourceName $script:DataSourceName `
            -Title  'Smoke OK (loopfix)' `
            -Symbol 'SPY' `
            -Side   'BUY' `
            -Status 'Open' `
            -EntryPx 500 `
            -Qty 1

        # Assert one POST happened
        Assert-MockCalled Invoke-RestMethod -ModuleName NotionTrader -Times 1 -ParameterFilter {
            $Method -eq 'Post' -and $Uri -like '*/v1/pages'
        }

        # Inspect the captured call (no ConvertFrom-Json to avoid format drift)
        $post = $script:Calls | Where-Object { $_.Method -eq 'Post' -and $_.Uri -like '*/v1/pages' } | Select-Object -Last 1
        $post | Should -Not -BeNullOrEmpty
        # Body should mention a data source style parent (implementation may resolve name->id internally)
        ($post.Body -match '"type"\s*:\s*"data_source') | Should -BeTrue
    }

    It "updates via PATCH to /v1/pages/<id> when -SessionId is supported" -Skip:(!(Get-Command Write-TradeJournalEntry).Parameters.ContainsKey('SessionId')) {
        $cmd = Get-Command Write-TradeJournalEntry -Module NotionTrader -ErrorAction Stop

        $null = & $cmd `
            -DataSourceName $script:DataSourceName `
            -Title  'Smoke OK (loopfix patch)' `
            -Symbol 'SPY' `
            -Side   'BUY' `
            -Status 'Open' `
            -EntryPx 500 `
            -Qty 1 `
            -SessionId 'abc123'

        Assert-MockCalled Invoke-RestMethod -ModuleName NotionTrader -Times 1 -ParameterFilter {
            $Method -eq 'Patch' -and $Uri -like '*/v1/pages/*'
        }

        $patch = $script:Calls | Where-Object { $_.Method -eq 'Patch' -and $_.Uri -like '*/v1/pages/*' } | Select-Object -Last 1
        $patch | Should -Not -BeNullOrEmpty
        ($patch.Body -match '"session_id"') | Should -BeTrue
    }

    AfterAll {
        Assert-VerifiableMocks
    }
}
