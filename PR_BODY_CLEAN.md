# Phase 1 — Clean Minimal (bar_replay + sample)

## Summary
- Introduces Phase 1 minimal baseline (6 files): .gitattributes, .gitignore, 	ools/bar_replay.py, scripts/make_sample_bars.ps1, scripts/convert_bars.ps1, data/AAPL_1m.csv.
- No heavy history; line endings normalized; sample CSV included for reproducibility.

## Testing
- python -m hybrid_ai_trading.tools.bar_replay --help OK
- One-pass demo against data/AAPL_1m.csv OK

## Notes
- Phase 1 static tag: phase1-static-20251026_024824
