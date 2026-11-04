# Pre-registered test 8: top-4 of the 10 biggest decliners, trailing-stop exits

Written and committed **before** `top4.py` was run (2026-11-04). Design from
the user: pick the 10 biggest decliners, rank the top 4 most likely to rise,
buy at the next open, exit only by a trailing stop, up to 50 positions,
S&P 500 large caps.

## Rules

| | Rule |
|---|---|
| Universe | S&P 500 members (from their date added), close >= $20, volume >= 1M shares |
| Candidates | Each day, the 10 biggest one-day % decliners, each down at least 2% |
| Skip | Next open +1.5% or more above the drop-day close (bounce already priced); already held |
| Ranking (price rule) | Deepest next-open gap first ("final flush"), ties by bigger drop; buy the top 4 |
| Entry | Next day's open |
| Size | 2% of account equity per position (1/50); at most 50 open; skip new buys if cash or slots run out |
| Exit | Trailing stop only. Stop = (highest close since entry, or the entry price if higher) x (1 - trail). Each day: if the open is at or below the stop, sell at the open; otherwise if the low reaches the stop, sell at the stop price. The high-water mark updates at each close (conservative with daily bars). No time limit |
| Trail | **Primary 3%** (user's choice). Also reported: 5%, 8%, and 2 x ATR(14) as a % of entry |
| Costs | 5 bps per side, plus 10 bps extra slippage on stop sales (stress: 20 bps). Cash earns T-bills (^IRX) |

## Controls and samples

- Controls (same exits and sizing): 4 random picks from the same top 10
  (average of 5 fixed seeds), and the 4 biggest drops (no gap ranking).
- Samples: S&P 500 2005-2015, S&P 500 2016-2026, S&P 400 mid caps 2005-2026,
  and the 835 US stocks over $2B outside the S&P 500/400.
- **No sample is fully fresh:** the final-flush signal was found in test 7 on
  S&P 500/400 and the 835 stocks. The real out-of-sample test is a forward
  paper log with the AI ranking.

## Pass criteria (primary: 3% trail, gap ranking, base costs, in ALL four samples)

1. Sharpe ratio (over T-bills) higher than SPY buy and hold.
2. Maximum drawdown smaller than SPY's.
3. Annual return above T-bills.
4. Sharpe higher than the random-pick control (ranking must add something).

Also reported: trade win rate, average win and loss, average days held,
average exposure, trades per year, the other trail levels, and stress costs.
