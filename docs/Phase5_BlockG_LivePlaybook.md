# Phase-5 Block-G – NVDA Live Playbook (Stub, 2025-12-08)

> **Status**: DESIGN-ONLY / STUB.  
> No live trading is launched by this playbook yet.  
> Block-E/F (EV + risk + CI) remain the gatekeepers.

---

## 1. Scope

- Symbol: **NVDA**
- Regime: **NVDA_BPLUS_LIVE**
- Account: **IB PAPER** first, real capital later.
- Style: ORB + VWAP micro-mode, tiny size, one-trade-at-a-time.

Block-G will eventually answer:

> "Given Phase-5 risk + EV are all green, *when* and *how* are we allowed to actually send a NVDA live trade?"

Right now, it is **documentation + stub runner only**.

---

## 2. Hard Preconditions (MUST be true before any Block-G live session)

Before *any* Block-G NVDA live session, all of the following must be satisfied:

1. **Phase-5 CI / Risk Green**
   - `tools\Run-Phase5MicroSuite.ps1` → all tests PASS
   - `tools\Run-Phase5EvPreflight.ps1` → PASS
   - `tools\Run-Phase5FullCI.ps1` → PASS

2. **Pre-market risk OK**
   - `tools\PreMarket-Check.ps1` returns **OK_TO_TRADE (exit code 0)**.
   - RiskPulse:
     - daily loss within limits,
     - no forced HALT flags.

3. **EV + EV-bands / hard veto OK**
   - EV anchors stable:
     - `Show-Phase5EvAnchors.ps1` shows:
       - NVDA_BPLUS_LIVE ev_orb_vwap_model ≈ 0.008
   - EV-bands config present:
     - `config\phase5_ev_bands.yml` has `NVDA_BPLUS_LIVE` entry.
   - EV hard-veto modes snapshot:
     - `Invoke-Phase5EvHardVetoDaily.ps1` has been run for the day,
     - Notion EV Hard Veto Daily shows modes consistent with today’s intent
       (e.g. NVDA may be LOG-ONLY during early Block-G).

4. **IB Gateway / IB API Ready**
   - IBG up and connected (paper account).
   - `tools\Test-IBAPI.ps1` reports OK for current session window.

5. **Operator Readiness**
   - Journaling page for the day prepared in Notion.
   - No fatigue / emotional red flags (manual self-check).

---

## 3. Phase-5 Block-G – First Live Rules (Concept)

When Block-G is eventually **armed**, the first version must obey:

1. **Size / Risk**
   - 1 contract / 1 share only (or equivalent tiny size).
   - R-per-trade is strictly capped and integrated with Phase-5 risk.
   - No scaling in, no averaging down, no revenge trading.

2. **Number of Trades**
   - Max **1 NVDA Block-G session** per day (stub: possibly 0).
   - Each session = at most **one micro-mode NVDA trade** (entry + exit).

3. **Time Window**
   - Only within the approved trading window in `utils\preflight.py`
     (e.g., regular session RTH; no after-hours scalping in v1).

4. **Strategy Envelope**
   - Trade must be consistent with:
     - NVDA_BPLUS_LIVE ORB + VWAP pattern,
     - EV >= configured band threshold,
     - Phase-5 risk gates all green (no overrides).

5. **Post-Trade AAR**
   - Every Block-G trade must be logged in:
     - Notion (NVDA Live journal),
     - CSV / JSONL (for automated EV vs PnL analysis).

---

## 4. Current Stub Implementation

As of this document:

- `tools\NvdaPhase5_BlockGStub.ps1`:
  - **does NOT call** any live NVDA runner yet.
  - prints:
    - current date + session info,
    - list of required preconditions,
    - a reminder that Block-G is not yet armed.
  - exit code = 0 if checklist script itself runs, regardless of market state.

- No Python live executor is wired specifically for Block-G yet
  (existing NVDA Phase-5 live runner is used only via separate tools).

---

## 5. Future Work for Block-G

1. **G.1 – Checklist Binding**
   - Tie `NvdaPhase5_BlockGStub.ps1` into:
     - `PreMarket-OneTap.ps1`
     - or a dedicated "NVDA Block-G Session" helper.
   - For now, keep it manual: operator runs Block-G stub explicitly.

2. **G.2 – Simulated Block-G Sessions (Paper Only)**
   - Use paper account but treat it with Block-G discipline and journaling.
   - One trade per day maximum, tracked as if real.

3. **G.3 – Full Block-G Live**
   - After sustained paper success and stable CI:
     - Allow very small real NVDA positions under Block-G rules.
     - Keep all Phase-5 risk / EV gates fully in charge.

Any change that actually sends live NVDA orders under Block-G must:

- update this playbook,
- be backed by replay / paper evidence,
- and pass FullCI + preflight before being considered “live-ready”.