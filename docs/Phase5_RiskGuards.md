# Phase-5 Risk Guards (Engine + RiskManager)

This document summarizes the current Phase-5 risk envelope as enforced by
`ExecutionEngine`, `RiskManager`, and the Phase-5 helpers/wrappers.

## 1. Engine-level guards

### 1.1 Phase-5 no-averaging-down engine guard

Location:

- `ExecutionEngine.place_order(...)` in
  `src/hybrid_ai_trading/execution/execution_engine.py`

Behavior:

- Triggered only when:

  - `risk_manager.phase5_no_averaging_down_enabled == True`, and  
  - `side.upper() == "BUY"`.

- Uses `portfolio_tracker.get_positions()` as source of truth:

  - Typical shape: `{"NVDA": {"size": 1.0, "avg_price": 1.0, "currency": "USD"}}`.

- For the requested `symbol`, it looks up an existing position:

  - From dict keys: `size`, `qty`, `quantity`, `position`, `shares`, or  
  - From attributes: `.size`, `.qty`, `.quantity`, `.position`, `.shares`.

- If `qty_existing > 0` for that symbol:

  - The new BUY is **rejected** immediately with:

    - `status = "rejected"`  
    - `reason = "no_averaging_down_phase5_engine_guard"`.

- If any error occurs inside this guard, it logs a debug message and **does not**
  block the trade; control falls back to RiskManagers normal gates.

### 1.2 Phase-5 risk gate dispatch

Still inside `ExecutionEngine.place_order(...)`:

- Computes `notional = qty * (price or 0.0)`.

- Dispatches to the RiskManager:

  - Preferred: `risk_manager.allow_trade(notional=notional, side=side)`.
  - Fallback: `risk_manager.approve_trade(symbol, side, qty, notional)`.

- If the risk gate returns `(ok = False, reason)`, the engine returns:

  - `{"status": "rejected", "reason": <reason or 'risk_check_failed'>}`.

This means the engine guard and RiskManager must both be happy for a trade
to proceed.

### 1.3 Phase-5 logging wrapper

Function:

- `place_order_phase5_with_logging(...)` in `execution_engine.py`.

Key points:

- Builds an event with:

  - `ts`, `symbol`, `side`, `qty`, `price`, `regime`.

- Calls `engine.place_order(...)` (which includes:

  - Engine-level no-averaging-down guard, and  
  - RiskManager allow/approve gates).

- Attaches the raw result as:

  - `event["order_result"]`.

- Derives a Phase-5 view:

  - `status = result["status"].lower()`  
  - `reason = result.get("reason", "")`  
  - `phase5_allowed = status not in {"rejected", "error"}`  
  - `phase5_reason = reason or ("risk_ok" if phase5_allowed else "risk_rejected")`.

- Appends JSONL to:

  - `logs/phase5_live_events.jsonl`.

- Best-effort forward to:

  - `hybrid_ai_trading.utils.paper_exec_logger.log_phase5_event` or
    `log_event` if present (never raises on logging failure).

### 1.4 Verified by live runner

Script:

- `src/hybrid_ai_trading/runners/nvda_phase5_live_runner.py`.

Typical pattern when `HAT_ENABLE_NVDA_PHASE5_LIVE=1` and
`HAT_PHASE5_DOUBLE_BUY_DEMO=1`:

1. First BUY:

   - `status = "filled"`  
   - `phase5_allowed = True`  
   - `phase5_reason = "risk_ok"`.

2. Second BUY in same process:

   - `status = "rejected"`  
   - `reason = "no_averaging_down_phase5_engine_guard"`  
   - `phase5_allowed = False`  
   - `phase5_reason = "no_averaging_down_phase5_engine_guard"`.

This exact pattern is visible in `logs/phase5_live_events.jsonl`.

## 2. RiskManager-level guards

### 2.1 Core daily risk rails (Phase-agnostic, inherited by Phase-5)

The RiskManager still enforces your global hedge-fund-grade rails, which
Phase-5 strategies inherit:

- **Daily loss cap**:

  - If daily P&L exceeds the configured loss limit (relative to
    `starting_equity`), the RiskManager refuses new trades
    (`allow_trade`/`approve_trade` returns rejected).

- **Max drawdown / equity floor**:

  - If equity falls below a configured floor, new trades are rejected.

- **Force-halt / kill switch**:

  - A configuration flag can hard-stop all new trades until reset.

- **Session window / calendar constraints**:

  - Preflight / calendar wiring ensures Phase-5 runners only operate inside
    your allowed trading windows.

### 2.2 Phase-5 no-averaging-down (RiskManager side)

RiskManager has Phase-5 helpers/adapters that also enforce no-averaging-down,
in addition to the engine-level guard:

- Config flags:

  - `phase5_no_averaging_down_enabled` on RiskManager, and  
  - `phase5["no_averaging_down_enabled"]` in config.

- Tests and helpers:

  - `tools/test_phase5_no_averaging_adapter_positions.py`  
  - `tools/test_phase5_no_averaging_hook.py`  
  - `tools/test_phase5_place_order_wrapper.py`.

These ensure that Phase-5 state and decisions are wired correctly, and that
no-averaging-down behavior is respected when the RiskManager is consulted.

### 2.3 Debug override for research

For research and debugging, you can deliberately disable the Phase-5
no-averaging behavior via:

- Environment variable:

  - `HAT_PHASE5_NOAVG_DISABLED=1` (used in `tools/debug_phase5_noavg_positions.py`).

When this is set:

- `build_live_config()` flips:

  - `phase5_no_averaging_down_enabled = False`, and  
  - `phase5["no_averaging_down_enabled"] = False`.

This is intended for controlled backtests / diagnostics, not for production.

## 3. Phase-5 micro suite

The current Phase-5 micro test suite consists of:

1. `tools/Test-Phase5Sanity.ps1`:

   - Checks presence/shape of key Phase-5 artifacts (NVDA/SPY/QQQ logs/CSVs).
   - Signals missing data (e.g. replay CSVs) as warnings for operator review.

2. `tools/Test-Phase5NoAveragingEngineGuard.ps1`:

   - Runs `tests/test_phase5_no_averaging_engine_guard.py` with `PYTHONPATH=src`.
   - Verifies:

     - With Phase-5 enabled: 2nd BUY is rejected with
       `"no_averaging_down_phase5_engine_guard"`.
     - With Phase-5 disabled: both BUYs are filled.

3. `tools/Run-Phase5MicroSuite.ps1`:

   - Orchestrates both scripts:

     - Runs `Test-Phase5Sanity.ps1`, then  
     - Resets CWD and runs `Test-Phase5NoAveragingEngineGuard.ps1`.

   - On success it prints:

     - `[Phase5] Micro suite completed successfully.`

This micro-suite is the recommended gate before promoting any Phase-5
changes to a live or pre-market pipeline.