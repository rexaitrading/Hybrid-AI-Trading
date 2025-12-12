# Block-G Contract Semantics (Single Source of Truth)

This document defines the ONLY accepted meanings of Block-G readiness fields.

## Contract file
- logs/blockg_status_stub.json

## Required fields
- as_of_date (YYYY-MM-DD) must equal local today (America/Vancouver)
- <symbol>_blockg_ready must exist for the requested symbol

## Exit codes (Check-BlockGReady.ps1)
- 0: READY (symbol field exists and true)
- 1: NOT READY (symbol field exists and false)
- 3: INVALID CONTRACT (missing required field OR stale date OR parse error)

## Notes
- Check-BlockGReady.ps1 is contract-only. It does not recompute readiness.
- Build-BlockGStatusStub.ps1 / Run-BlockGReadiness.ps1 are allowed to recompute and write the contract.