# Phase 1 — Bar Replay (ORB) + Sample + Env Hardening

## Scope
- 	ools/bar_replay.py (ORB mode, --force-exit, --no-notion switch).
- Sample data + helper scripts.
- Environment hardening: scripts/activate_safe.ps1, equirements-phase1.txt, UTF-8 pip configs (no BOM).
- Tests: smoke suite passing on Windows.

## Validation
- python -m pytest -q tests/smoke → **11 passed**.
- Dev clone outside OneDrive; pip check → **No broken requirements**.

## Tag
- Static baseline: phase1-static-20251026_024824
