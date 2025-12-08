# Phase-5 EV Tuning (Block-E, 2025-11-30)

This note captures the **per-trade EV** and **EV bands** that were locked in
during the Block-E ORB + VWAP micro-mode tuning session on 2025-11-30.

These values are now wired into:

- `config/phase5/ev_simple.json`
- `config/phase5_ev_bands.yml`
- NVDA / SPY / QQQ Phase-5 CSV writers:
  - `tools/nvda_phase5_paper_to_csv.py`
  - `tools/spy_phase5_paper_to_csv.py`
  - `tools/qqq_phase5_paper_to_csv.py`

---

## 1. Per-trade EV (fractional PnL space)

All EVs are **per trade**, expressed in *fractional PnL* units
(e.g. `0.0123` ~ +1.23% on notional for a typical trade).

| Regime           | EV per trade | Notes                            |
| ---------------- | ------------ | -------------------------------- |
| NVDA_BPLUS_LIVE  | 0.0123       | NVDA B+ live / replay micro-mode |
| SPY_ORB_LIVE     | 0.0075       | SPY ORB Phase-5 live / paper     |
| QQQ_ORB_LIVE     | 0.0075       | QQQ ORB Phase-5 live / paper     |

Source of truth: `config/phase5/ev_simple.json`.

- `NVDA_BPLUS_LIVE` is stored as a scalar value.
- `SPY_ORB_LIVE` and `QQQ_ORB_LIVE` are stored under `ev_per_trade`
  inside their objects.

---

## 2. EV bands (`ev_band_abs`) used by Phase-5 gating

EV bands are kept in *fractional PnL* units and currently equal the
per-trade EVs above (simple 1Ãƒâ€” band for this checkpoint).

They live in `config/phase5_ev_bands.yml` and are loaded via
`config.phase5_config_loader.load_phase5_ev_bands()` /
`get_ev_band_abs()`.

YAML snapshot:

```yaml
nvda_bplus_live:
  ev_band_abs: 0.0123

spy_orb_live:
  ev_band_abs: 0.0075

qqq_orb_live:
  ev_band_abs: 0.0075
```

---

## 3. Block-E EV vs Realized (RequireEv = ON)

- NVDA_BPLUS_LIVE:
  - Trades (SELL, EV-wired): 6
  - AvgRealized: 0.020000
  - AvgEV:       0.012300
  - EV_needed/trade (0.7% daily, N=6): 0.001167
  - EV / EV_needed ratio: 10.54x

- SPY_ORB_LIVE:
  - Trades (SELL, EV-wired): 7
  - AvgRealized: 0.020000
  - AvgEV:       0.007500
  - EV_needed/trade (0.7% daily, N=7): 0.001000
  - EV / EV_needed ratio: 7.50x

- QQQ_ORB_LIVE:
  - Trades (SELL, EV-wired): 7
  - AvgRealized: 0.020000
  - AvgEV:       0.007500
  - EV_needed/trade (0.7% daily, N=7): 0.001000
  - EV / EV_needed ratio: 7.50x

This is a **paper / replay tuning checkpoint**, not live-capital PnL.

---

## 4. How to re-tune later

1. Update EV per trade in `config/phase5/ev_simple.json`.
2. Update `ev_band_abs` in `config/phase5_ev_bands.yml`.
3. Re-run the EV sanity helpers (e.g. `Invoke-Phase5EvSanity`).
4. Append a new section to this file and create a new checkpoint tag.

## TODO: EV â†’ Gate Policy (to be finalized)

Planned structure (not yet enforced in code):

- For each regime (NVDA_BPLUS_LIVE, SPY_ORB_LIVE, QQQ_ORB_LIVE):
  - Define EV bands in terms of |EV| and/or EV_PER_TRADE.
  - Define when EV alone can:
    - Soft veto (log-only),
    - Raise band from 0 â†’ 1 â†’ 2,
    - Trigger a hard veto suggestion for the risk layer.

- Align thresholds with:
  - ev_gap_sweep.py thresholds (0.02, 0.03, 0.05, 0.07, 0.10, 0.15, 0.20),
  - Notion \"All Band-1 EV\" cross-symbol view.

Implementation will be done via:
- risk_phase5_ev_bands.py
- phase5_gating_helpers.py
- live runner EV logging (ev_orb_vwap_model, ev_effective_orb_vwap)## Authoritative EV band thresholds (Block-E, ORB+VWAP micro-mode)

These values summarize the current working assumptions for EV per trade
and the minimum EV needed to pass the EV-band gate (Band-0 → Band-1)
for our three live regimes:

- NVDA_BPLUS_LIVE:
  - ev_per_trade ≈ 0.02
  - band_min_ev (Band-1 threshold) ≈ 0.01

- SPY_ORB_LIVE:
  - ev_per_trade ≈ 0.0075
  - band_min_ev (Band-1 threshold) ≈ 0.0038

- QQQ_ORB_LIVE:
  - ev_per_trade ≈ 0.0075
  - band_min_ev (Band-1 threshold) ≈ 0.0038

These thresholds are currently encoded in:

- Python helper: `risk_phase5_ev_bands._EV_BAND_TEST_CONFIG`
- EV tuning snapshot: `docs/Phase5_EvTuning_Snapshot.md`
- (Planned) YAML: `config/phase5_ev_bands.yml`

Going forward, Phase-5 EV gating code (risk_phase5_ev_bands.py +
phase5_gating_helpers.py) should treat these as the single source of truth
for Band-0/Band-1 boundaries when evaluating EV-based gates.