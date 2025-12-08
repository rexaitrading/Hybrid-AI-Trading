# Phase-5 NVDA Paper EV Policy

**As of 2025-12-08**, NVDA Phase-5 paper JSONL (`logs\nvda_phase5_paperlive_results.jsonl`) uses:

- `"ev": null`
- `"ev_band_abs": null`
- `"phase5_ev_band_enabled": false`

by **design**.

Rationale:

- NVDA paper runs are treated as a **pure EV-agnostic baseline**:
  - They capture realized PnL and Phase-5 risk decisions (no-averaging, daily loss cap).
  - They do **not** inject the ORB/VWAP model EV (0.008 ≈ 0.8% per trade) into the JSONL.
- The NVDA ORB/VWAP EV anchor is defined separately in:
  - `config\phase5\nvda_orb_ev_model.json`
  - `tools\Show-NvdaOrbEvModel.ps1`

Implications:

- Notion NVDA paper views should **not** expect `ev` / `ev_band_abs` to be present for paper rows.
- EV vs realized analysis for NVDA is done by:
  - Comparing realized PnL from NVDA B+ replay / paper,
  - Against the **model EV** from `nvda_orb_ev_model.json`, not from the paper JSONL `ev` field.

If this policy changes in the future (e.g., enabling NVDA paper EV logging), this document must be updated and tagged with a new checkpoint.