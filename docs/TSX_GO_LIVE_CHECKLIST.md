TSX / TSXV GO-LIVE CHECKLIST (Stack 3)

GOAL:
- Add TSX/TSXV safely without breaking Block-G, Phase-5 risk, or ops stability.

A) BEFORE YOU BUY FEEDS
- Confirm you will trade TSX/TSXV >= 3 days/week for >= 4 weeks.
- Confirm you have a symbol universe + strategy definition for TSX names.
- Confirm you will log Provider QoS (freshness/latency/errors) for Canada tape.

B) MINIMUM FEEDS (Tier A)
- Enable IBKR Canadian Exchange Group L1 (TSX/TSXV).
- Keep all vendor feeds OFF until you prove a bottleneck.

C) VALIDATION DAY (PAPER-AS-LIVE)
- Run premarket:
  - tools\Check-IBGReady.ps1
  - tools\Check-BlockGReady.ps1 -Build -Symbol ALL -Quiet
  - pytest risk slice (Block-G tests first)
- Start streaming + record QoS:
  - tools\Write-ProviderQos.ps1 -Provider IBKR -Channel realtime -Symbol RY.TO -FreshnessMs 0 -LatencyMsP95 0 -ErrorRate1m 0 -Ok $true
- Verify QoS checks pass:
  - tools\Check-ProviderQos.ps1 -Quiet

D) WHEN TO UPGRADE TO VENDOR FEEDS (Tier B)
Only upgrade if you can demonstrate:
- stale ticks/bars in IBKR feed,
- replay mismatch harming Phase-1/Phase-2,
- scanner/backfill gaps.
Choose ONE: QuoteMedia OR Barchart (not both initially).

E) WHEN TMX DIRECT IS JUSTIFIED (Tier C)
Only if:
- TSX/TSXV becomes major PnL source,
- you need lowest-latency source tape,
- you can budget $500$2000+/mo.
Then integrate TMX feed as price check / redundancy first; dont immediately switch primary routing.

F) FAILOVER DRILLS (MANDATORY)
- Kill primary feed session; confirm:
  - Provider QoS ledger records the event,
  - fallback source is used for price checks only,
  - Block-G stays fail-closed if data goes stale.

G) COST GUARDRAILS
- Update logs\provider_cost_actuals.json weekly.
- Run tools\Check-ProviderCostCaps.ps1; if cap exceeded, disable optional feeds first.