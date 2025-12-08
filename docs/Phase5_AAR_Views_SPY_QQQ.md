# Phase-5 AAR Views for SPY / QQQ (Notion Alignment)

This document describes the intended After-Action Review (AAR) Notion views
for SPY and QQQ Phase-5 ORB replay.

## Data sources

- SPY: `logs\spy_phase5_paper_for_notion.csv`
- QQQ: `logs\qqq_phase5_paper_for_notion.csv`

Each CSV should contain at least:

- `ts`
- `symbol`
- `regime`
- `side`
- `price`
- `realized_pnl_paper`
- `ev`
- `ev_band_abs`
- `ev_gap_abs`
- `ev_hit_flag`
- `phase5_allowed`
- `phase5_reason`

## Recommended Notion views

### 1. SPY ORB – EV vs PnL (AAR)

- Filter:
  - `symbol` = `SPY`
  - `regime` = `SPY_ORB_REPLAY`
- Properties (visible):
  - `ts`, `side`, `price`
  - `realized_pnl_paper`
  - `ev`, `ev_band_abs`, `ev_gap_abs`, `ev_hit_flag`
  - `phase5_allowed`, `phase5_reason`
- Sort:
  - `ts` ascending (for replay review)
  - or `date` descending (for daily summary)

### 2. QQQ ORB – EV vs PnL (AAR)

- Filter:
  - `symbol` = `QQQ`
  - `regime` = `QQQ_ORB_REPLAY`
- Properties and sort pattern same as SPY.

### 3. EV Hard Veto Daily – SPY / QQQ modes

- Data source: `logs\phase5_ev_hard_veto_daily.csv`
- Notion table:
  - `date`
  - `modes` (e.g. `SPY_LOG_ONLY`, `QQQ_LOG_ONLY`, `SPY_LIVE`, `QQQ_LIVE`)
  - `live_count`
- Filter:
  - `date` = Today (for daily AAR),
  - or last N days for streak review.

## Usage

- Run `.\tools\Invoke-Phase5EvHardVetoDaily.ps1` and `.\tools\Run-Phase5EvPreflight.ps1`
  before importing CSVs into Notion.
- Use these views during daily AAR to:
  - Verify EV vs realized PnL behaviour for SPY / QQQ ORB,
  - Confirm EV hard-veto modes and live_count are consistent with expectations.