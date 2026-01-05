# HybridAITrading Gate Matrix (Fail-Closed)

This document is the single authority for "what is done" across the 7 phases.
A phase is DONE only when its gates are GREEN with recorded evidence (exit codes + artifacts).

## Phase-1: Bars Integrity + Session Semantics (Foundation)
**Gate P1-A (Bars completeness)**
Command: `tools\Test-BarCompleteness.ps1 -Symbol NVDA -BarsPath <bars> -Window RTH`
Pass: exit 0, logs `[BAR-CHECK] OK ... cadence_sec=60 count>=390`

**Gate P1-B (Session boundaries)**
Command: `tools\Test-SessionBoundaries.ps1 -Symbol NVDA -BarsPath <bars>`
Pass: exit 0, logs include `RTH>=10` (e.g., `PRE=...,RTH=...`)

**Gate P1-C (Session tag normalization artifact)**
Command: `tools\Normalize-SessionTags.ps1 -BarsPath <bars>`
Pass: exit 0 AND produces `<bars_basename>.session.csv`

**Phase-1 LOCK RULE**
Compact timestamps (`yyyyMMdd  HH:mm:ss`) are interpreted as **ET-local** and converted to UTC internally.

## Phase-5: Controlled Paper/Live Safety (Block-G)
Gate P5-A: `tools\Run-BlockGLockPack.ps1 -Symbol NVDA` exit 0
Gate P5-B: `pytest -q tests/test_execution_engine_phase5_guard.py` exit 0
Gate P5-C: Every NVDA live order calls `tools\Check-BlockGReady.ps1 -Symbol NVDA` and fails closed on non-zero

(Other phases are tracked in docs/ROADMAP.md and docs/OPS_Readiness_Phase1to7.md)
