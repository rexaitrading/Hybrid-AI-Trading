# Phase-5 EV Tuning Snapshot

*Generated:* 2025-12-01 22:37:35

## NVDA_BPLUS_LIVE

- SELL LIVE trades analyzed : ~14
- Mean realized pct          : ~0.0070 (0.70% per trade)
- Realized pct stdev         : ~0.0097
- **Data-driven EV candidate**      : 0.0070
- **Data-driven band candidate**    : 0.0049 (≈ 0.5 * stdev)
- **Decision (Phase-5 now)**        : Keep NVDA as *EV-only, no EV-band* for live gating.

## SPY_ORB_LIVE

- Config EV (ev_simple.json)        : 0.0075
- Config band (phase5_ev_bands.yml) : 0.0056
- Synthetic LIVE sells              : realized_pct ≈ 0.02 per trade
- Heuristic band (0.75 * EV)        : 0.005625
- **Decision**                       : Keep band = 0.0056 (no change).

## QQQ_ORB_LIVE

- Config EV (ev_simple.json)        : 0.0075
- Config band (phase5_ev_bands.yml) : 0.0056
- Synthetic LIVE sells              : realized_pct ≈ 0.02 per trade
- Heuristic band (0.75 * EV)        : 0.005625
- **Decision**                       : Keep band = 0.0056 (no change).

## Summary of Decisions

- NVDA_BPLUS_LIVE: remain EV-only (no EV-band gating yet), but future EV/band wiring can use EV ≈ 0.0070 and band ≈ 0.0049.
- SPY_ORB_LIVE: EV = 0.0075, band = 0.0056 (unchanged).
- QQQ_ORB_LIVE: EV = 0.0075, band = 0.0056 (unchanged).