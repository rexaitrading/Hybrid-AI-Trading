# Asia Session Equivalence + Monday Proof Plan

## Session equivalence (from Resolve-RunContext calendar_id + market_tz)
- US (XNYS, America/New_York): RTH is required for ALL_STRICT open-day checks.
- JP (XTKS, Asia/Tokyo): use Tokyo regular session (day session) as the RTH-equivalent.
- HK (XHKG, Asia/Hong_Kong): regular day session as RTH-equivalent.
- SG (XSES, Asia/Singapore): regular day session as RTH-equivalent.
- IN (XNSE, Asia/Kolkata): regular day session as RTH-equivalent.
- KR (XKRX, Asia/Seoul): regular day session as RTH-equivalent.
- TW (XTAI, Asia/Taipei): regular day session as RTH-equivalent.

## Monday proof plan (single choke point at a time)
### Step 1 — Session gate proof (per market)
During each market’s regular session:
- Run Resolve-RunContext and confirm:
  - market_closed_today=false
  - is_trading_day=true
  - session_name == RTH-equivalent

### Step 2 — Open-day receipts (US first)
During US RTH:
- Build stub + Check-BlockGReady (ALL_STRICT)
- Record first NOT READY reason.
- Fix only that gate (Phase23 -> EV-hard daily -> GateScore LIVE -> semantics FULL_LIVE_ELIGIBLE).

### Step 3 — Asia replication
Repeat Step 2 per market (JP/HK/SG/IN/KR/TW) during each market’s session window.

## Command snippets (CHECK)
- Build stub:
  tools/Build-BlockGStatusStub.ps1 -Market <MKT> -Symbol NVDA
- Check readiness:
  tools/Check-BlockGReady.ps1 -Market <MKT> -Symbol NVDA -Mode ALL_STRICT
