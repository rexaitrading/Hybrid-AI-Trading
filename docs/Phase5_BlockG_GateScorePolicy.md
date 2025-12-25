# Phase-5 Block-G GateScore Freshness Policy

## LIVE readiness policy (holiday/weekend-safe)

LIVE readiness requires:
- gatescore_fresh_for_session == true
- gatescore_recent_enough == true (age_days <= MAX_GS_AGE_DAYS)
- gatescore_samples_ok == true
- gatescore_threshold_ok_today == true
- per-symbol `<sym>_blockg_ready == true`

`gatescore_fresh_today` is informational only and may be false on holidays/weekends.

## Rationale
On holidays/weekends there may be no “today” session row. Using most-recent-session age keeps the system fail-closed while avoiding false lockouts.
