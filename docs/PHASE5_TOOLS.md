# Phase 5 Risk Toolkit  Overview

This document summarizes the Phase 5 (Controlled Live) risk tools and tests built for ORB/VWAP micro-mode.

---

## 1. Config & Sketches

**Files:**

- `config/orb_vwap_aapl_thresholds.json`
- `config/orb_vwap_nvda_thresholds.json`
- `config/orb_vwap_spy_thresholds.json`
- `config/orb_vwap_qqq_thresholds.json`

**Phase5-specific:**

- AAPL / NVDA: have `phase5_risk_sketch` with:
  - `no_averaging_down`
  - `min_add_cushion_bp`
  - `daily_loss_cap_pct`
  - `daily_loss_cap_notional`
  - `symbol_daily_loss_cap_bp`
  - `symbol_max_trades_per_day`
  - `max_open_positions`
- SPY / QQQ: no `phase5_risk_sketch` on purpose; EV sweeps show no edge after costs, so they remain Phase5-disabled.

---

## 2. Phase 5 Risk Policy (code-level)

**Core policy (mirrors tests/test_phase5_risk_policy.py):**

- File: `tests/test_phase5_risk_policy.py`
- Policy function (in test harness):
  - `can_add_position(risk_cfg, pos, symbol, daily_state) -> (bool, reason)`

**Key rules:**

1. **No averaging down**
   - If `unrealized_pnl_bp <= 0`  block.
   - If `unrealized_pnl_bp < min_add_cushion_bp`  block.

2. **Account-level daily loss caps**
   - If `account_pnl_pct <= daily_loss_cap_pct`  block.
   - If `account_pnl_notional <= daily_loss_cap_notional`  block.

3. **Symbol-level caps**
   - If `symbol.pnl_bp <= symbol_daily_loss_cap_bp`  block.
   - If `symbol.trades_today >= symbol_max_trades_per_day`  block.

4. **Portfolio-level caps**
   - If `open_positions >= max_open_positions`  block.

When all conditions pass, Phase 5 gate returns `can_add = True`.

---

## 3. Phase 5 Tools

### 3.1 Schema Validator

- File: `tools/phase5_risk_schema_validator.py`
- Purpose:
  - Type-check and sanity-check `phase5_risk_sketch` in threshold JSONs.
- Typical usage:
  - CLI:
    - `python tools/phase5_risk_schema_validator.py config/orb_vwap_aapl_thresholds.json config/orb_vwap_nvda_thresholds.json config/orb_vwap_spy_thresholds.json config/orb_vwap_qqq_thresholds.json`
- Behavior:
  - AAPL / NVDA  `phase5_risk_sketch OK`.
  - SPY / QQQ  no phase5_risk_sketch (OK if Phase5 disabled).

### 3.2 Phase 5 Risk Diff Tool

- File: `tools/Diff-Phase5Configs.ps1`
- Purpose:
  - Compare Phase5 risk sketch fields between two ORB/VWAP configs (e.g. AAPL vs NVDA).
- Default behavior:
  - Compares:
    - `NoAveragingDown`
    - `MinAddCushionBp`
    - `DailyLossCapPct`
    - `DailyLossCapNotional`
    - `SymbolDailyLossCapBp`
    - `SymbolMaxTradesPerDay`
    - `MaxOpenPositions`
- Typical usage (PowerShell):
  - `.\tools\Diff-Phase5Configs.ps1`
  - Or:
    - `.\tools\Diff-Phase5Configs.ps1 -Left config\orb_vwap_aapl_thresholds.json -Right config\orb_vwap_nvda_thresholds.json`

### 3.3 AAPL Phase 5 Risk Sketch Tool

- File: `tools/aapl_orb_phase5_risk_sketch.py`
- Purpose:
  - Load `phase5_risk_sketch` from AAPL JSON and construct `RiskConfigPhase5`.
- Output:
  - Pretty-prints all fields in `RiskConfigPhase5`.
  - Shows the JSON `notes` explaining the policy.

### 3.4 Mock TradeEnginePhase5 Runner (Lab-Only)

- File: `tools/mock_phase5_trade_engine_runner.py`
- Purpose:
  - Simulate a tiny TradeEnginePhase5 loop that calls `can_add_position()` with Phase5 config.
- Supported symbols:
  - `--symbol AAPL`
  - `--symbol NVDA`
- Behavior:
  - Loads `RiskConfigPhase5` from corresponding JSON.
  - Runs a fixed set of scenarios:
    - Losing position  blocks averaging down.
    - Flat position  blocks averaging down.
    - Winner below cushion  block.
    - Winner above cushion  allow.
    - Daily loss cap breached  block.
    - Symbol loss cap breached  block.
    - Max trades per day reached  block.
    - Max open positions reached  block.

---

## 4. Tests and CI Hooks

### 4.1 Unit Test: Phase 5 Risk Policy Harness

- File: `tests/test_phase5_risk_policy.py`
- Tests:
  - No averaging down (negative / zero PnL).
  - Min cushion logic.
  - Daily loss cap (notional).
  - Symbol loss cap and max trades.
  - Happy path (all caps OK).

### 4.2 CLI Micro-Test: Tools Sanity

- File: `tests/test_phase5_risk_cli_tools.py`
- Tests:
  1. **Schema validator CLI**
     - Runs `python tools/phase5_risk_schema_validator.py ...` against all four configs.
     - Asserts exit code == 0.
  2. **Diff tool CLI (Windows-only)**
     - Runs `powershell -File tools/Diff-Phase5Configs.ps1` for AAPL vs NVDA.
     - Asserts exit code == 0.
     - Skipped on non-Windows via `pytest.mark.skipif`.

---

## 5. How to Run the Phase 5 Suite Locally

From repo root (PowerShell):

1. **Phase 5 unit tests only:**
   - `python -m pytest tests/test_phase5_risk_policy.py`

2. **Phase 5 CLI tools test:**
   - `python -m pytest tests/test_phase5_risk_cli_tools.py`

3. **All Phase 5 lab tools manually (optional):**
   - `python tools/phase5_risk_schema_validator.py config/orb_vwap_aapl_thresholds.json config/orb_vwap_nvda_thresholds.json config/orb_vwap_spy_thresholds.json config/orb_vwap_qqq_thresholds.json`
   - `.\tools\Diff-Phase5Configs.ps1`
   - `python tools/mock_phase5_trade_engine_runner.py --symbol AAPL`
   - `python tools/mock_phase5_trade_engine_runner.py --symbol NVDA`