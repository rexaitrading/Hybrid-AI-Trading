# Notion: NVDA LIVE EV vs PnL surfaces

## Main DB
- URL: https://www.notion.so/2970bf31ef1580a6983ecf2c836cf97c
- Database: Trading Journal, Edge Feed, and 4 more

## Views

### 1. NVDA LIVE – EV vs PnL
- Filters:
  - symbol = NVDA
  - regime = NVDA_BPLUS_LIVE
- Important properties:
  - ev
  - realized_pnl_paper
  - ev_vs_realized_paper = ev - realized_pnl_paper
  - ev_gap_abs = abs(ev_vs_realized_paper)
  - ev_hit_flag = EV_HIT / EV_MISS / EV_ZERO (Formula)
  - ev_hit_bucket = EV_HIT / EV_MISS / EV_ZERO (Select, for grouping)
- Conditional colors:
  - EV_HIT = green
  - EV_MISS = red
  - EV_ZERO = grey

### 2. NVDA LIVE – EV Summary
- Filters:
  - symbol = NVDA
  - regime = NVDA_BPLUS_LIVE
  - ts = This week (relative to today)
- Group:
  - Group by ev_hit_bucket (EV_HIT, EV_MISS, EV_ZERO)
  - Use group size visually to see counts per week.

### 3. NVDA LIVE – EV MISS (Big) [optional]
- Filters:
  - symbol = NVDA
  - regime = NVDA_BPLUS_LIVE
  - ev_hit_flag = EV_MISS
  - ev_gap_abs > threshold
- Journal field: ev_miss_journal = "What did I learn from this EV_MISS?"
