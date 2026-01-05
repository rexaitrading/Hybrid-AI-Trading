# NVDA LIVE READY = TRUE (Decision Table)

**LIVE is allowed only when ALL are true:**

| Gate | Source of truth | Condition | Fail-closed behavior |
|---|---|---|---|
| Phase-4 today | logs/phase4 artifact (or harness output) | phase4_ok_today == true | block live |
| Phase-2/3 health | logs/phase23_health_daily.csv | phase23_health_ok_today == true | block live |
| EV-hard veto today | logs/phase5_ev_hard_veto_daily.csv | ev_hard_daily_ok_today == true | block live |
| GateScore fresh + quality | logs/gatescore summary | gatescore_fresh_today == true AND thresholds+samples OK | block live |
| Block-G contract | logs/blockg_status_stub.json | nvda_blockg_ready == true | block live |
| PS checker | tools/Check-BlockGReady.ps1 | exit code == 0 | block live |
| Operator arm token | tools/Arm-NVDA-Live.ps1 / stamp JSON | valid for today | block live |
| IB chokepoint | src/.../broker/ib_safe.py | enforced before placeOrder | cannot bypass |

**Truth rule:** PowerShell `Check-BlockGReady.ps1` remains the semantic owner for contract semantics; Python enforces and fails closed.
