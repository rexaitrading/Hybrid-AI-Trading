# AAPL ORB/VWAP Notion View  EV-based (g  0.04, training-only)

**Context**

These rows come from:

- JSONL: research/aapl_orb_vwap_replay_trades_enriched.jsonl
- Thresholds: config/orb_vwap_aapl_thresholds.json (gatescore_edge_ratio_min = 0.04, max_cost_bp = 3.0)

Each trade has (at minimum):

- symbol = "AAPL"
- regime = "AAPL_ORB_VWAP_REPLAY"  (or similar regime string)
- pnl_pct / gross_pnl_pct
- r_multiple
- cost_bp (cost in basis points)
- edge_ratio (or gate_score / score_v2)
- any existing Risk/Phase5 tags

---

## 1. Recommended Notion Properties (Columns)

In the **AAPL ORB/VWAP** database (or Trading Journal if shared):

Create/confirm properties:

- **Name** (Title)  e.g. "AAPL ORB/VWAP 2025-01-03"
- **symbol** (Select/Text)  "AAPL"
- **regime** (Select/Text)  AAPL_ORB_VWAP_REPLAY
- **ts_trade** (Date/Time)
- **pnl_pct** or **gross_pnl_pct** (Number, Percent)
- **r_multiple** (Number)
- **edge_ratio** or **gate_score_v2** (Number)
- **cost_bp** (Number)
- **notes** (Rich text)

---

## 2. Recommended View: "AAPL ORB g0.04 EV-clean (training)"

Create a new view in Notion:

- View name: `AAPL ORB g0.04 EV-clean (training)`
- Type: Table

### Filters

Set filters to:

- symbol **is** AAPL
- regime **is** AAPL_ORB_VWAP_REPLAY
- edge_ratio (or gate_score_v2) **is on or after** 0.04
- cost_bp **is on or before** 3
- pnl_pct / gross_pnl_pct **is on or after** 0   (optional but matches EV-clean stance)

### Sort

Sort by:

1. edge_ratio / gate_score_v2 **descending**
2. ts_trade **ascending** (optional)

This will show:

- Only AAPL ORB/VWAP trades in replay regime
- With EV-based thresholds (edge_ratio  0.04, cost  3 bp)
- Best AAPL ORB ideas at the top

---

## 3. Training-only Policy

In your notes / dashboard description, clearly mark:

- AAPL ORB/VWAP is **training/mocked only** in Phase 5.
- No live size until:
  - more replays are added,
  - EV is stable across larger samples,
  - Phase 5 risk tests pass (no averaging down, daily caps, etc.).