# Phase 2 — Microstructure + EV / GateScore Plan

**As of 2025-12-08**, Phase-5 EV + CI is locked and tagged:

- EV anchors:
  - NVDA: `config\phase5\nvda_orb_ev_model.json` + `tools\Show-NvdaOrbEvModel.ps1`
  - SPY:  `config\phase5\spy_orb_ev_model.json` + `tools\Show-SpyOrbEvModel.ps1`
  - QQQ:  `config\phase5\qqq_orb_ev_model.json` + `tools\Show-QqqOrbEvModel.ps1`
- EV-bands: `config\phase5_ev_bands.yml`
- EV preflight: `tools\Run-Phase5EvPreflight.ps1`
- Full CI: `tools\Run-Phase5FullCI.ps1`

This doc defines the first **Phase-2 microstructure hooks** into EV / GateScore.

---

## 1. Goals for Phase-2

1. Keep Phase-5 risk stable:
   - No changes to Phase-5 gating behaviour in this phase.
   - All microstructure work is **log-only / diagnostic** at first.
2. Start wiring **microstructure features** into:
   - EV diagnostics (replay + paper),
   - GateScore / EV models (longer-term).
3. Make microstructure features visible in:
   - CSVs under `logs\*phase5*_for_notion*.csv`,
   - Notion views used for AAR.

---

## 2. Existing microstructure / GateScore modules

Code already present:

- `src\hybrid_ai_trading\microstructure.py`
- `src\hybrid_ai_trading\gatescore.py`
- `src\hybrid_ai_trading\gatescore_bar.py`

Smokes:

- `tools\microstructure_ev_smoke.py`
- `tools\Run-MicrostructureEvSmoke.ps1`

These confirm that the modules import correctly and are callable inside the venv.

---

## 3. Target features for first hook (log-only)

Phase-2 initial focus (P2.1–P2.3):

1. Simple **range / volatility descriptor**:
   - Example: `(high - low) / open` or similar per ORB bar.
2. Simple **micro-trend descriptor**:
   - Example: sign of (close - vwap) or short-term momentum flag.
3. Optional: **spread / liquidity proxy** (if cheap to compute from available data).

These will be attached to ORB replay / paper rows as *additional columns*, not used in risk yet.

---

## 4. Where to log microstructure first

### 4.1 SPY / QQQ ORB replay / paper

Targets:

- SPY:
  - `logs\spy_phase5_paper_for_notion_ev_diag.csv`
  - `logs\spy_phase5_paper_for_notion_journal_ev_bands.csv`
- QQQ:
  - `logs\qqq_phase5_paper_for_notion_ev_diag.csv`
  - `logs\qqq_phase5_paper_for_notion_journal_ev_bands.csv`

Plan:

- Add new columns such as:
  - `ms_range_pct`
  - `ms_trend_flag`
- Populate them via a small helper in `tools\*paper_to_csv.py` OR a dedicated enrich script.

### 4.2 NVDA (later)

- NVDA is already EV-agnostic in paper JSONL by design.
- Microstructure hooks for NVDA will be added **after** SPY/QQQ ORB replay hooks are stable.

---

## 5. Concrete micro-blocks (next steps)

### P2.1 — Microstructure Feature Discovery (log-only)

- Use `tools\Run-MicrostructureEvSmoke.ps1` + a new small Python demo to:
  - Inspect available functions / classes in `microstructure.py` and `gatescore_bar.py`.
  - Identify 1–2 functions suitable for computing:
    - a range/volatility metric,
    - a simple trend/momentum flag.

### P2.2 — Add microstructure fields to SPY ORB diagnostics

- Update `tools\spy_phase5_paper_to_csv.py` (or a related enrich tool) to:
  - Compute `ms_range_pct`, `ms_trend_flag` from ORB bars or derived data.
  - Write them into `spy_phase5_paper_for_notion_ev_diag.csv`.
- Ensure:
  - All Phase-5 tests still green,
  - EV preflight + FullCI still pass.

### P2.3 — Mirror the same pattern for QQQ

- After SPY wiring is stable, replicate the microstructure fields for QQQ:
  - `qqq_phase5_paper_for_notion_ev_diag.csv`,
  - `qqq_phase5_paper_for_notion_journal_ev_bands.csv`.

### P2.4 — Notion alignment for microstructure

- Add microstructure columns (`ms_range_pct`, `ms_trend_flag`, etc.) to:
  - SPY ORB AAR view,
  - QQQ ORB AAR view.
- Use them in AAR to study:
  - Which microstructure regimes align with positive EV and realized PnL.

---

## 6. Guardrails

- No Phase-5 risk behaviour change in Phase-2:
  - Microstructure wiring is **log-only**.
  - Gating remains controlled by existing EV / EV-bands / risk modules.
- Every change must be validated by:
  - `tools\Run-Phase5MicroSuite.ps1`
  - `tools\Run-Phase5EvPreflight.ps1`
  - `tools\Run-Phase5FullCI.ps1`

This document is the anchor for Phase-2 microstructure work. Any future change
to microstructure → EV / GateScore wiring must reference and update this plan.