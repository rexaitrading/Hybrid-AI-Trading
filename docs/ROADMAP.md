# Hybrid AI Day-Trade System — 7-Phase ROADMAP (Institutional)

**Repo baseline:** Block-G enforced at IB transmit chokepoint + PS semantic owner + LockPack truthful.

## Phase 1 — Data Ingestion & Bar Replay
**Required**
- [ ] Authoritative bar source selection contract (per symbol/day)
- [ ] Bar completeness validation (missing bars => fail-closed)
- [ ] Session boundary normalization (pre/RTH/post tags)
- [ ] Replay metadata journal (replay_id, data_hash, source, bar_count)

**Optional**
- [ ] Multi-venue cross-check (IB vs Polygon/Alpaca sanity)
- [ ] Replay speed controls (×1 ×5 ×20)
- [ ] Visual replay inspector UI

## Phase 2 — Microstructure & Cost Model
**Required**
- [ ] Latency model (signal→order→exchange)
- [ ] Spread-aware fill model (bid/ask vs mid)
- [ ] Partial fill modeling
- [ ] Volatility-scaled slippage
- [ ] Per-symbol cost profiles

**Optional**
- [ ] Adaptive cost model (learned from fills)
- [ ] Time-of-day cost curves
- [ ] L2-aware cost modeling

## Phase 3 — Strategy Logic (Edge Generation)
**Required**
- [ ] Formal strategy contract (inputs→outputs→invariants)
- [ ] Signal confidence scoring
- [ ] Minimum sample enforcement
- [ ] Strategy self-diagnostics (“why did I fire?”)

**Optional**
- [ ] Strategy ensembles
- [ ] Regime-conditional strategies
- [ ] Strategy A/B testing harness

## Phase 4 — Validation & Edge Proof
**Required**
- [ ] Phase-4 daily artifact: phase4_passed_today
- [ ] Edge metrics: expectancy/hit/drawdown
- [ ] Sample sufficiency rules
- [ ] Drift invalidation (auto-fail)

**Optional**
- [ ] Walk-forward validation
- [ ] Monte-Carlo equity curves
- [ ] Regime-segmented validation

## Phase 5 — Risk, Gating & Block-G
**Verified**
- Block-G enforced in: execution engine + order manager + IB adapter + IB chokepoint
- PS = semantic owner; operator live-arm token; closed-day semantics; LockPack truthful

**Required next**
- [ ] Block-G JSON schema v1 (versioned)
- [ ] Python contract reader helper (no recompute)
- [ ] Per-symbol readiness flags (NVDA/SPY/QQQ)
- [ ] Today-ness validation for Phase23/EV-hard/Phase4

**Optional**
- [ ] Auto-lock after loss thresholds
- [ ] Unlock cooldown rules
- [ ] Risk budget allocator

## Phase 6 — Intel & Regime
**Required**
- [ ] Intel → regime mapper
- [ ] Risk overrides from events (CPI/FOMC/earnings)
- [ ] Fail-closed on missing intel when required

**Optional**
- [ ] Volatility shock detector
- [ ] Cross-asset correlation alerts
- [ ] AI macro summarizer

## Phase 7 — Portfolio & Capital Scaling
**Required**
- [ ] Portfolio VAR
- [ ] Cross-symbol exposure caps
- [ ] Capital scaling rules
- [ ] Daily capital re-baseline

**Optional**
- [ ] Multi-strategy allocator
- [ ] Kelly dampening
- [ ] Investor-grade reporting
