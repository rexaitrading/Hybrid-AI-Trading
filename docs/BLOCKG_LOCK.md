# Block-G Institutional Lock (Single Authority)

## Semantic Owner (MUST)
- **tools\\Check-BlockGReady.ps1** is the **single semantic owner** of LIVE readiness.
- Python execution path must **fail-closed** based on its exit code.
- No module may “recompute” Block-G semantics in Python.

## Exit Codes (Contract)
- **0**  -> READY (LIVE eligible)
- **10** -> CLOSED DAY DIAGNOSTIC OK (pipeline healthy; LIVE remains disallowed)
- **!=0,10** -> NOT READY (fail-closed)

## Allowlist: READY execution callers (execution-only)
Only these scripts may EXECUTE Check-BlockGReady.ps1:
- tools\\Arm-NVDA-Live.ps1  (LIVE arming must remain fail-closed)
- tools\\Check-BlockGDiagnosticOk.ps1  (ops wrapper: maps exit=10 -> 0)
- tools\\Test-BlockGWeekendSemantics.ps1 (regression test)

## One-shot institutional lock verification
Run:
- tools\\Run-BlockGLockPack.ps1

It verifies:
1) closed-day semantics (ready=10, diag=0)
2) no-bypass (READY execution allowlist)
3) READY executor list == Arm-NVDA-Live only
4) Python import sanity (IBAdapter + Phase5 guard)
