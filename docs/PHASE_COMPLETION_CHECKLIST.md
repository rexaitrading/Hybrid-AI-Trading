# Phase Completion Checklist (CI-Enforced)

## Global invariants (must always hold)
- [ ] UTF-8 no-BOM + LF everywhere
- [ ] Fail-closed on missing daily artifacts
- [ ] LockPack truthful (python import sanity fail-closed)
- [ ] Block-G enforced at IB transmit chokepoint

## Phase 1 Gate (Data/Replay)
- [ ] Bar source contract written (symbol/day)
- [ ] Bar completeness passes (no gaps)
- [ ] Session tags correct (pre/RTH/post)
- [ ] Replay journal written (hash, count, source)

## Phase 2 Gate (Microstructure/Costs)
- [ ] Slippage/commission defined per symbol
- [ ] Spread-aware fill model active
- [ ] Latency model active
- [ ] Partial fills modeled or explicitly disabled (with reason)

## Phase 3 Gate (Strategy)
- [ ] Strategy contract doc exists
- [ ] Signal payload includes: trigger reason + confidence
- [ ] Minimum sample gates enforced

## Phase 4 Gate (Validation)
- [ ] Phase4 artifact for TODAY exists and is PASS
- [ ] Sample sufficiency met
- [ ] Drift checks green

## Phase 5 Gate (Risk/Block-G)
- [ ] Block-G status JSON exists for TODAY
- [ ] nvda_blockg_ready == true (for live)
- [ ] Check-BlockGReady.ps1 exit == 0 (for live)
- [ ] Operator arm token valid (for live)

## Phase 6 Gate (Intel/Regime)
- [ ] Intel pipeline ran today
- [ ] Regime computed
- [ ] Event risk overrides evaluated

## Phase 7 Gate (Portfolio)
- [ ] Portfolio VAR within limits
- [ ] Exposure caps satisfied
- [ ] Scaling rules satisfied
