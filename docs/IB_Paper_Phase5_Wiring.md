# IB Paper Phase-5 Wiring (Draft v0.1)

This document describes how to wire Phase-5 risk into IB paper account runners.

## 1. Goal

- Any order submitted to IB paper account must pass:
  - account_daily_loss_gate
  - account/no-averaging-down gate (via RiskManager.check_trade_phase5)
  - symbol-specific caps (SPY_ORB, QQQ_ORB, NVDA_B+ slices)

before actually calling the IB client (ibapi / TWS).

## 2. Pattern (mirrors in-process paper runners)

1. Engine / runner constructs a trade dict for the proposed order.
2. Call guard_phase5_trade(rm, trade) to obtain a Phase5RiskDecision.
3. If decision.allowed is False:
   - Do NOT send order to IB.
   - Log blocked reason + details.
4. If allowed:
   - Translate trade dict into ibapi order and submit.

## 3. Next wiring steps (not yet implemented)

- Identify IB-facing runners (tools/*ibg* or *paper_live_ib* scripts).
- Replace direct calls to IB/TWS place_order with a wrapper similar to:
  - execution_engine_phase5_guard.place_order_phase5_with_guard, but for IB API.
- Ensure RiskManager has access to:
  - account-wide realized_pnl (for account_daily_loss_gate)
  - symbol positions (for no-averaging-down gate)

## Pre-market guardrails (Phase-5)

This is the safety chain that must pass before any Phase-5 session is considered OK to trade:

- **CI microsuites**
  - `phase5-microsuite.yml` → runs `pytest tests -k "phase5" -q` with `PYTHONPATH=src`.
  - `portfolio-microsuite.yml` → runs:
    - `tests/test_portfolio_tracker_full.py`
    - `tests/test_execution_engine_phase5_guard.py`

- **Local helpers**
  - `tools\Run-Phase5Tests.ps1`
    - Uses repo `.venv` and `PYTHONPATH=src`.
    - Runs the same `-k "phase5"` slice as CI.
  - `tools\Run-PortfolioExecTests.ps1`
    - Runs the portfolio/exec microsuite (`test_portfolio_tracker_full.py` + `test_execution_engine_phase5_guard.py`).

- **Pre-market macro checks**
  - `tools\PreMarket-Check.ps1`
    - Loads latest RiskPulse snapshot (day PnL, max DD, daily loss cap, hedge status).
    - Aggregates provider QoS (IBKR primary, TMX fallback, etc.).
    - Now also runs both Phase-5 microsuites before declaring `OK_TO_TRADE`.

- **One-tap launcher**
  - `tools\PreMarket-OneTap.ps1`
    - PowerShell wrapper (PS 5.1-safe, UTF-8 no BOM).
    - Always runs, in order:
      1. `tools\Run-Phase5Tests.ps1`
      2. `tools\Run-PortfolioExecTests.ps1`
      3. `tools\PreMarket-Check.ps1`
    - If any step fails → aborts with a clear `[ONETAP] ... FAILED` message.
    - When called with parameters, e.g.:
      - `.\tools\PreMarket-OneTap.ps1 -Symbol NVDA -Session 2025-11-19`
      it launches:
      - `python .\tools\PreMarket-OneTap.py --symbol NVDA --session 2025-11-19`
      only after all guardrails are green.
    - When called without `-Symbol` / `-Session`, runs in **guardrails-only** mode (tests + PreMarket-Check, Python runner skipped).

This ensures that **Phase-5 risk**, **portfolio/exec wiring**, and **RiskPulse + Provider QoS** are always green before any OneTap-driven session is allowed to proceed.