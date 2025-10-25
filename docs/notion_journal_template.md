# Notion Trading Journal — Bar Replay (Import CSV)

Create a **Database** in Notion with these properties (match names EXACTLY):

| Property Name | Type           | Description |
|---|---|---|
| ts            | Date/Time      | Decision timestamp (bar time). |
| symbol        | Text           | Ticker. |
| price         | Number         | Close price at decision bar. |
| setup         | Select         | Strategy tag (e.g., MomentumBurst, VWAPReclaim, ReversalSniffer). |
| side          | Select         | BUY / SELL. |
| qty           | Number         | Theoretical shares. |
| kelly_f       | Number         | Kelly fraction used by sizer. |
| confidence    | Number         | [0..1] confidence from ensemble. |
| reason        | Text           | Short reason string from model. |
| regime        | Select         | Market regime tag (neutral/bull/bear/volatile). |
| sentiment     | Number/Text    | Optional signal sentiment. |
| notes         | Text           | Human notes during review. |
| entry_px      | Number         | (From simulator) entry fill price. |
| exit_px       | Number         | (From simulator) exit fill price. |
| gross_pnl     | Number         | Gross PnL for the trade. |
| slippage      | Number         | Entry+exit total slippage. |
| fees          | Number         | Fees for the trade. |
| net_pnl       | Number         | Net PnL (gross - fees). |

**Import flow**
1. Run `replay_engine.py` → produces `logs/replay_journal.csv`.
2. Import that CSV into this Notion DB.
3. After running `pnl_simulator.py`, import/merge `replay_journal.sim.csv` (or add the PnL fields to existing entries).
