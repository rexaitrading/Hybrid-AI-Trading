# Phase-2 Microstructure Fields — SPY / QQQ

As of 2025-12-08, Phase-2 microstructure enrichment is **log-only** and applies to:

- `logs\spy_phase5_paper_for_notion_ev_diag_micro.csv`
- `logs\qqq_phase5_paper_for_notion_ev_diag_micro.csv`

These files are produced by:

- `tools\Run-SpyQqqMicrostructureEnrich.ps1`
    - which calls `tools\spy_qqq_microstructure_enrich.py`
    - and uses `hybrid_ai_trading.microstructure.compute_microstructure_features`.

## New columns

The enrichment currently adds two diagnostic columns:

- `ms_range_pct`
    - Definition: `abs(window_ret)` from `MicrostructureFeatures`.
    - Intuition: simple range/volatility descriptor over the recent window.
- `ms_trend_flag`
    - Definition: `sign(last_ret)` ∈ { -1, 0, +1 }.
    - Intuition:
        - `+1` → recent return positive (micro up-trend)
        - `-1` → recent return negative (micro down-trend)
        - `0`  → flat / no clear micro-move

## Usage

- Treat these as **Phase-2 diagnostic features only**:
    - They do **not** affect Phase-5 gating or position sizing.
    - They are intended for Notion AAR views and future GateScore work.
- Recommended:
    - Add `ms_range_pct` and `ms_trend_flag` to SPY/QQQ ORB AAR Notion views
      to study how microstructure regimes align with EV and realized PnL.

Any change to these definitions or additional microstructure fields should update this doc and be validated via:

- `tools\Run-Phase5MicroSuite.ps1`
- `tools\Run-Phase5EvPreflight.ps1`
- `tools\Run-Phase5FullCI.ps1`