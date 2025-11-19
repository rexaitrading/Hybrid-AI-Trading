# NVDA B+ Notion View  g0.04 EV-Clean Trades

**Context**

These rows come from:

- JSONL: research/nvda_bplus_replay_trades_g0.04_enriched.jsonl
- Charts: charts/nvda_bplus_g0.04/NVDA_BPLUS_YYYY-MM-DD.png

Each trade has (at minimum) the following fields:

- symbol = "NVDA"
- side = "long"
- ts_trade = "2025-01-03T09:30:00" (trade timestamp)
- session = "RTH"
- regime = "NVDA_BPLUS_REPLAY"
- bar_replay_tag / replay_id = "NVDA_BPLUS_2025-01-03"
- screenshot_path = "charts/NVDA_BPLUS_2025-01-03.png"
- tp_pct, sl_pct
- gross_pnl_pct
- r_multiple
- kelly_f
- gate_rank (1 = best)
- gate_bucket ("A", "B", "C")
- pnl_rank
- gate_score_v2 (approximately 0.050.08 for this sample)

---

## 1. Recommended Notion Properties (Columns)

In your **NVDA B+ replay** database, create or confirm these properties:

1. **Name** (Title)  
   - Value: use bar_replay_tag (e.g. NVDA_BPLUS_2025-01-03).  
   - The Python push script likely already sets this.

2. **symbol** (Text or Select)  
   - Map from JSON field symbol (always NVDA for this view).

3. **ts_trade** (Date/Time)  
   - Map from JSON field ts_trade.

4. **side** (Select)  
   - Values like long, short.  
   - Here: long.

5. **regime** (Select or Text)  
   - Map from JSON field regime.  
   - For this view: value NVDA_BPLUS_REPLAY.

6. **session** (Select)  
   - Use values like RTH, PRE, etc.  
   - Here: RTH.

7. **outcome** (Select)  
   - Map from outcome (e.g. EOD, TP, SL).

8. **gate_bucket** (Select)  
   - Map from gate_bucket (A, B, C).  
   - A = best, then B, then C.

9. **gate_rank** (Number)  
   - Map from gate_rank (1 = best).

10. **gate_score_v2** (Number, 3 decimals)  
    - Map from gate_score_v2 (e.g. 0.051, 0.064, 0.077).

11. **pnl_rank** (Number)  
    - Map from pnl_rank.

12. **gross_pnl_pct** (Number, Format = Percent)  
    - JSON field: gross_pnl_pct (e.g. 0.008, 0.010, 0.012).

13. **r_multiple** (Number, 3 decimals)  
    - Map from r_multiple (approximately 0.020.03).

14. **kelly_f** (Number, 3 decimals or Percent)  
    - Map from kelly_f (close to gross_pnl_pct in this synthetic sample).

15. **bar_replay_tag** (Text)  
    - Map from bar_replay_tag (e.g. NVDA_BPLUS_2025-01-03).

16. **replay_id** (Text)  
    - Map from replay_id (same as bar_replay_tag in this sample).

17. **screenshot_path** (Text or URL)  
    - Map from screenshot_path (e.g. charts/NVDA_BPLUS_2025-01-03.png).  
    - Optional: store a Notion File/Image property separately and manually attach the PNG.

18. **notes** (Rich text)  
    - Map from notes (NVDA B+ replay EOD (labels=True heuristic=False)).

---

## 2. Recommended View: NVDA B+ g0.04 EV-clean

Create a **new view** in this database:

- View name: NVDA B+ g0.04 EV-clean  
- Type: Table

### 2.1 Filters

Set filters so this view only shows the g0.04 EV-clean trades we just pushed:

1. symbol **is** NVDA  
2. regime **is** NVDA_BPLUS_REPLAY  
3. gate_score_v2 **is on or after** 0.04  
4. gross_pnl_pct **is on or after** 0      (optional but recommended)  
5. session **is** RTH                       (optional)  
6. outcome **is** EOD                       (optional)

If you have a dedicated property for the bar tag or replay id, you can optionally restrict to this exact specimen:

- bar_replay_tag **starts with** NVDA_BPLUS_2025-01-

(so this view shows the 2025-01-03, 06, 07 examples we pushed from g0.04).

### 2.2 Sorts

Set default sort order:

1. Sort 1: gate_bucket ascending  
   - Desired order: A  B  C.  
   - If Notion sorts alphabetically, that already matches A/B/C.

2. Sort 2: gate_rank ascending  
   - 1 is best, then 2, then 3.

3. Sort 3 (optional): ts_trade ascending  
   - So earlier replay days appear first.

This gives you a table where:

- Top rows are gate_bucket A, lowest gate_rank (best signals),  
- Then B, then C,  
- Only EV-clean gate_score_v2  0.04 trades appear at all.

---

## 3. Recommended Visible Columns in this View

For the NVDA B+ g0.04 EV-clean view, show columns in this order:

1. Name (title; bar tag like NVDA_BPLUS_2025-01-03)  
2. ts_trade (date/time)  
3. symbol  
4. regime  
5. session  
6. side  
7. gate_bucket  
8. gate_rank  
9. gate_score_v2  
10. pnl_rank  
11. gross_pnl_pct  
12. r_multiple  
13. kelly_f  
14. outcome  
15. bar_replay_tag  
16. replay_id  
17. screenshot_path  
18. notes  

Hide less critical raw fields if they exist (internal IDs, debug flags, etc.).

---

## 4. How This Aligns with g0.04 EV-Clean Trades

- All data in this view must come from:  
  - nvda_bplus_replay_trades_g0.04_enriched.jsonl  
  - Pushed via:  
    - tools/nvda_bplus_push_to_notion.py --jsonl research/nvda_bplus_replay_trades_g0.04_enriched.jsonl

- By filtering on:  
  - symbol = NVDA  
  - regime = NVDA_BPLUS_REPLAY  
  - gate_score_v2  0.04  
  - gross_pnl_pct  0  

you ensure the Notion dashboard only shows **EV-clean, g0.04-gated NVDA B+ replays** for Block E.NVDA-EV2.

Once this is configured, you can duplicate this pattern later for:

- Different gate thresholds (e.g., g0.06, g0.08),  
- Different symbols (AAPL, SPY, QQQ) once their EV labs are mature.
---

## 5. Extended NVDA B+ EV sweep (synthetic raw_multi_ext)

On 2025-11-19 we extended the NVDA B+ replay sample via:

- Input: research/nvda_bplus_replay_trades.bak_enrich.jsonl (1 base trade)
- Extended: research/nvda_bplus_replay_trades.raw_multi_ext.jsonl (5 synthetic trades)
- Enriched: research/nvda_bplus_replay_trades.raw_multi_ext_enriched.jsonl

Sweep result on gate_score_v2:

- N = 5 trades overall
- For thresholds from -0.10 to 0.02, mean_pnl_pct  0.008, mean_ev  0.008
- For gate_score_v2  0.04: count=3, mean_pnl_pct0.010, mean_ev0.010
- For gate_score_v2  0.06: count=2, mean_pnl_pct0.011, mean_ev0.011

Given the tiny sample and good EV across all cuts, we keep the working cutoff:

- NVDA B+ GateScore v2 cutoff: **0.04** (g0.04)
- This matches the NVDA B+ g0.04 EV-clean Notion view, and we treat this sweep as a sanity check, not a threshold change.
---

## 5. Extended NVDA B+ EV sweep (synthetic raw_multi_ext)

On 2025-11-19 we extended the NVDA B+ replay sample via:

- Input: research/nvda_bplus_replay_trades.bak_enrich.jsonl (1 base trade)
- Extended: research/nvda_bplus_replay_trades.raw_multi_ext.jsonl (5 synthetic trades)
- Enriched: research/nvda_bplus_replay_trades.raw_multi_ext_enriched.jsonl

Sweep result on gate_score_v2:

- N = 5 trades overall
- For thresholds from -0.10 to 0.02, mean_pnl_pct  0.008, mean_ev  0.008
- For gate_score_v2  0.04: count=3, mean_pnl_pct0.010, mean_ev0.010
- For gate_score_v2  0.06: count=2, mean_pnl_pct0.011, mean_ev0.011

Given the tiny sample and good EV across all cuts, we keep the working cutoff:

- NVDA B+ GateScore v2 cutoff: **0.04** (g0.04)
- This matches the NVDA B+ g0.04 EV-clean Notion view, and we treat this sweep as a sanity check, not a threshold change.