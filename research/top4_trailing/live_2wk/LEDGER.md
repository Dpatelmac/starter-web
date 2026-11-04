# Two-week ledger: top 4 unexplained S&P 500 losers, trailing stop

**Illustration only:** 10 trading days is far too short to judge a strategy.
Not pre-registered; no trades were sent.

- Drop days 2026-10-21 to 2026-11-03; buys at the next open (Oct 22 to Nov 4);
  open positions marked at the 2026-11-04 close.
- Each day: the 10 biggest S&P 500 decliners (down 2%+, close >= $20, volume
  >= 1M). Removed if explained: earnings the evening before or that day
  (Yahoo earnings dates), or an 8%+ gap down at the open. Bought the 4
  biggest remaining losers (fewer when fewer were left).
- Analyst actions and other news were **not** checked.
- $1,000 per trade; 5 bps per side plus 10 bps on stop sales.
- Trailing stop from the highest close since entry (or the entry price): sell
  at the open if it opens below the stop, otherwise at the stop when the day's
  low touches it.
- "E" = the company reported earnings while the position was held, which the
  user's framework would have skipped.

## Every buy and sell (3% trailing stop)

| Date | Buys (next-day open) | Sells |
|---|---|---|
| 2026-10-22 | DXCM $79.90 (fell -6.4%), CMG $28.09 (fell -5.2%; E), EXPE $281.79 (fell -5.0%), SBAC $172.74 (fell -4.2%) | DXCM $77.50 (-3.2%, stop) |
| 2026-10-23 | MRNA $196.69 (fell -17.6%), COHR $207.85 (fell -12.5%), LITE $760.00 (fell -11.5%), FLEX $76.22 (fell -11.1%) | EXPE $289.54 (+2.5%, stop), MRNA $190.79 (-3.2%, stop), LITE $737.20 (-3.2%, stop), FLEX $73.93 (-3.2%, stop) |
| 2026-10-26 | GL $155.62 (fell -8.1%), T $20.70 (fell -8.0%), TMUS $145.81 (fell -7.7%; E), MGM $28.30 (fell -4.9%; E) | – |
| 2026-10-27 | DASH $168.77 (fell -6.1%; E), CHTR $102.01 (fell -5.9%), RDDT $138.39 (fell -4.0%), PYPL $55.41 (fell -3.6%; E) | SBAC $180.34 (+4.2%, stop) |
| 2026-10-28 | VLO $390.33 (fell -9.2%), MPC $438.97 (fell -7.4%), PSX $270.53 (fell -7.0%; E), PAYX $108.20 (fell -5.6%) | MGM $27.68 (-2.4%, stop), RDDT $134.24 (-3.2%, stop) |
| 2026-10-29 | – | COHR $232.40 (+11.6%, stop), VLO $378.62 (-3.2%, stop), MPC $427.55 (-2.8%, stop) |
| 2026-10-30 | TER $277.54 (fell -5.4%) | TER $269.21 (-3.2%, stop) |
| 2026-11-02 | DDOG $235.51 (fell -11.5%), QCOM $166.44 (fell -11.1%) | DDOG $228.44 (-3.2%, stop) |
| 2026-11-03 | MRVL $174.28 (fell -12.7%), CIEN $293.20 (fell -11.3%), P $117.33 (fell -10.4%), INTC $61.33 (fell -8.8%) | TMUS $155.35 (+6.3%, stop), DASH $184.37 (+9.0%, stop), PSX $273.78 (+1.0%, open gap), PAYX $112.03 (+3.3%, stop), QCOM $161.45 (-3.2%, stop), MRVL $169.05 (-3.2%, stop) |
| 2026-11-04 | LEN $90.20 (fell -5.4%), DHI $152.44 (fell -5.0%) | CIEN $291.08 (-0.9%, stop), P $114.12 (-2.9%, stop), INTC $58.74 (-4.4%, open gap) |
Still open at the Nov 4 close: CMG +25.1% (E), GL +3.8%, T +5.4%, CHTR +17.8%,
PYPL +8.5% (E), LEN +2.1%, DHI +2.9%.

Explained drops removed per drop day: Oct 21: 2, Oct 22: 1, Oct 23: 4,
Oct 26: 2, Oct 27: 6, **Oct 28: 10 (no buys on Oct 29)**, Oct 29: 9, Oct 30: 8,
Nov 2: 1, Nov 3: 8. Almost all were earnings reactions (peak earnings season).

## Totals

| | 3% stop | 8% stop |
|---|---|---|
| Trades | 29 (7 still open) | 29 (16 still open) |
| Profitable | 14 (48%) | 17 (59%) |
| Total P&L on $1,000 per trade | **+$583** | **+$978** |
| Average per trade | +2.0% | +3.4% |
| Excluding the trades held through earnings | 23 trades, 39% profitable, +$107, +0.5% avg | 17 trades, 47% profitable, +$11, +0.1% avg |

Most of the profit came from positions held through an earnings report (CMG
+25%, TMUS, DASH, PYPL); without them both versions are close to break-even.
Files: `candidates.csv` (all 100 candidates and why each was skipped),
`trades_3pct.csv`, `trades_8pct.csv`, `summary.json`, `ledger.py`.
