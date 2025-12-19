# Phase-7 Portfolio Optimizer Policy (Fail-Closed)

## Objective
Convert Phase-6 strategy scores into portfolio weights while enforcing risk constraints.

## Fail-Closed Rule
If any required input is missing, malformed, stale, or constraints fail:
- ok = false
- weights = {}
- reasons populated

## Inputs (v0 scaffold)
- Phase-6 daily summary (CSV) containing `strategy_id` and optionally `score`
- RunContext (mode/day_id) for traceability

## Outputs
- allocation.json (weights + metadata)
- allocation.csv (tabular audit)

## Constraints (v0 placeholders)
- max gross exposure
- max single name exposure
Future:
- VAR budget / stress
- correlation buckets
- liquidity / ADV caps
- regime-aware exposure throttles

## Safety Notes
- Optimizer must never override Block-G readiness.
- Any LIVE path still requires Phase-5 guard + Block-G enforcement.