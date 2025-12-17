# Phase-6 Strategy Router Policy

## Purpose
Phase-6 introduces a *multi-strategy / multi-symbol* execution layer that:
- selects which strategy may run,
- aggregates risk across strategies/symbols,
- produces portfolio-level logs and Notion artifacts,
- and integrates Phase-5 Block-G / RunContext so LIVE orders are always fail-closed.

This policy defines the minimum architecture and invariants Phase-6 must satisfy.

---

## Definitions

### Strategy ID
A stable identifier used everywhere (logs, Notion, risk aggregation, routing):
- NVDA_BPLUS
- SPY_ORB
- QQQ_ORB
- (future) ETH_1H, BTC_15M, etc.

### Run Modes
Run mode is authoritative and must be carried by RunContext:
- REPLAY: historical / bar-replay only
- PAPER: paper execution (no Block-G gating)
- LIVE: live execution (Block-G required)
- NOTION: export-only runs (no trading)

---

## Strategy Registry Contract

### Registry responsibilities
The registry is the single source of truth for:
- mapping strategy_id -> callable strategy implementation
- symbol universe and allowed order types
- timeframes / session constraints
- default risk budget configuration per strategy

### Minimal registry shape
Each registered strategy MUST define:

- strategy_id (string)
- symbol (string)
- timeframe (string, e.g. 1m, 5m)
- supports_modes (set: REPLAY/PAPER/LIVE)
- signal_fn(market_state) -> signal object
- order_plan_fn(signal, ctx, portfolio_state) -> order intents
- logs_schema_version (int)

---

## Router Responsibilities (Fail-Closed)

### Router is the policy gate for Phase-6
Router must fail-closed whenever:
- RunContext is missing or inconsistent
- Block-G is not READY for LIVE mode for that symbol
- portfolio risk limits would be breached
- strategy is not registered / not allowed in current mode

### Router flow (conceptual)
1) Load RunContext (single truth)
2) Load registry
3) For each strategy eligible today:
   - compute signal
   - compute order intent
   - portfolio risk aggregation check (global)
   - per-strategy risk check (local)
   - if LIVE: Block-G check + Python guard check
   - submit via execution engine
4) Log per-intent + per-fill
5) Write daily portfolio summary artifact

---

## Portfolio Risk Aggregation (Global)

Phase-6 introduces cross-strategy constraints that are stronger than per-strategy constraints.

### Minimum required risk limits
- Global daily loss cap (portfolio)
- Global max gross exposure
- Global max net exposure
- Per-symbol max exposure
- Max concurrent open positions
- Max correlated exposure bucket (e.g., NVDA + QQQ + SPY share market beta)
- Cooldown after consecutive losers (portfolio level)

### Example aggregation checks
- If portfolio daily PnL <= daily_loss_cap -> BLOCK all new orders (fail-closed)
- If adding proposed order would exceed max_gross -> BLOCK
- If strategy is in cooldown window -> BLOCK
- If correlated bucket exposure too high -> BLOCK

Phase-6 must produce explicit reason codes for every BLOCK decision.

---

## Logging & Artifacts (Institutional)

### Per-order intent log (JSONL)
Path: logs/portfolio_order_intents.jsonl

Each line should include:
- ts_utc
- run_mode
- day_id
- strategy_id
- symbol
- intent_id (uuid)
- side / qty / price / order_type
- gates:
  - blockg_ok (bool)
  - phase5_guard_ok (bool)
  - portfolio_risk_ok (bool)
  - strategy_risk_ok (bool)
- block_reason (string or null)

### Per-fill log (JSONL)
Path: logs/portfolio_fills.jsonl
Include:
- intent_id
- broker/exchange (IBKR/CCXT/etc.)
- fill qty/price
- commissions/slippage (Phase-2 costs)
- realized/unrealized pnl snapshot

### Daily portfolio summary (CSV)
Path: logs/phase6_portfolio_daily_summary.csv
One row per day:
- date
- symbols traded
- strategies active
- realized pnl
- max drawdown
- gross/net exposure snapshots
- count orders / count fills
- block counts by reason

---

## Notion Export Policy

Phase-6 must output a single “Daily Portfolio Summary” artifact suitable for Notion import:
- date
- total pnl
- strategy breakdown
- block reasons counts
- risk flags (portfolio OK, Block-G OK, etc.)

Phase-6 must not require Notion network access during trading. Export should be a separate mode (RunMode.NOTION).

---

## Integration Requirements

### Phase-5 Block-G
- LIVE orders require: Block-G READY for that symbol on that day
- Router must never submit a LIVE intent if Check-BlockGReady for that symbol is not OK
- Python guard must enforce the same gate at order submission time

### Phase-2 Costs
- Router must compute “effective notional” after costs for portfolio exposure tracking
- Costs must be deterministic in PAPER/REPLAY

### RunContext
RunContext is shared by:
- Router
- execution engine
- Notion exporter
- premarket checks

Router must pass RunContext into engines/adapters.

---

## Minimum deliverables for Phase-6 completion
1) strategies/registry.py (register strategies)
2) portfolio/router.py (dispatch + fail-closed)
3) portfolio/risk_aggregator.py (global checks + reason codes)
4) tests: registry loads + router blocks on missing Block-G in LIVE + logging file created
