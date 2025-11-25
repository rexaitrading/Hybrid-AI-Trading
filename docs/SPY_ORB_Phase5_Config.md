# SPY ORB Phase-5 Config (Draft v0.1)

This file captures *spec* values only. Live engine flags are **not** wired
to this yet. It is a design anchor for future wiring.

## 1. R Basis (from latest replay)

- Example trade:
  - r_multiple = 2.0
  - gross_pnl_pct ≈ +0.638%
- Implied:
  - 1R ≈ 0.319%
  - To hit +0.7% in a single trade on a similar day:
    - R_needed ≈ 2.2R

## 2. Proposed R-based thresholds

### 2.1 Take-profit (TP)

- Target: **TP_R = +2.2R**
  - Roughly +0.7% on days similar to the sample.
  - Keeps the micro-mode idea: "one clean winner per day ≈ 0.7%".

### 2.2 Stop-loss (SL)

- Proposed: **SL_R = -0.6R**
  - Approx −0.19% per full SL (0.319% * 0.6).
  - Reward:Risk ≈ 2.2 / 0.6 ≈ 3.7:1.
  - Tolerant of small shakeouts but cuts losers fast.

## 3. Phase-5 Risk Rails for SPY ORB

### 3.1 Daily loss cap (SPY ORB slice)

- Proposed: **daily_loss_cap_R = -3.0R** for SPY ORB.
  - E.g. three full SLs, or equivalent.
  - Combined with global account caps in RiskManager.

(When wired, this would map to a dollar-based cap through 1R sizing.)

### 3.2 Max trades per day

- Proposed: **max_spy_orb_trades_per_day = 3**
  - Encourages high-quality ORB attempts only.
  - Interaction with daily_loss_cap_R:
    - Worst case: 3 losses × -0.6R = -1.8R on SPY ORB slice.

## 4. Gate Behavior

- `phase5_base_allowed`:
  - EV / PnL-based ORB signal checks.
- `phase5_risk_allowed`:
  - Result of:
    - daily_loss_gate
    - no_averaging_down_gate
- `phase5_no_avg_allowed`:
  - No-averaging-down helper.
- `phase5_combined_allowed`:
  - Final AND of base + risk + no_avg gates.

SPY ORB Phase-5 views in Notion should continue to filter on:

- symbol = SPY
- regime = SPY_ORB_REPLAY / SPY_ORB_LIVE
- phase5_combined_allowed (checked / unchecked)

## 5. Alignment with Micro-Mode Target

- Daily micro-mode target: **+0.7% or better**.
- With TP_R = +2.2R and SL_R = -0.6R:
  - A single TP day ≈ +0.7% (per current sample).
  - A 50% win rate with these thresholds implies strong positive expectancy.
- Phase-5 risk rails (daily loss cap, no averaging down) ensure:
  - No revenge trading after losses.
  - No pyramiding into losers.
  - Controlled downside per day.

Future iterations will refine TP/SL and R basis as more SPY ORB replay
trades accumulate in the Phase-5 logs.