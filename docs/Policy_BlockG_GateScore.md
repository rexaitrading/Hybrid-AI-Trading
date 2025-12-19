# Block-G GateScore Policy

## Purpose
Block-G is a fail-closed live-permission contract. NVDA live is allowed only when:
- Phase-4 passed today
- EV-hard veto daily snapshot exists and passed today
- GateScore is fresh (REAL), has enough samples, and is above threshold
- Check-BlockGReady.ps1 exits 0
- Python execution path enforces the same contract before every NVDA live order

## Current state (2025-12-16)
- GateScore mean_edge_ratio observed: ~0.02
- Interim NVDA min_edge_ratio set to 0.02 to validate plumbing end-to-end.

## Threshold ladder (tighten over time)
- Stage A (plumbing): min_edge_ratio = 0.02
- Stage B (early edge): min_edge_ratio = 0.05
- Stage C (strong edge): min_edge_ratio = 0.10
- Stage D (institutional): min_edge_ratio = 0.20–0.30

Only advance to the next stage after:
- ≥ 10 trading days with stable REAL samples
- No Block-G false positives (live allowed on bad days)
- Post-mortem review + Notion journal update

## Operational preflight
Use: tools/Run-NvdaBlockGPreflight.ps1  
This script produces paperlive, builds contract, checks readiness, validates python enforcement, and snapshots logs/blockg_status_stub_GOOD_LAST.json.
