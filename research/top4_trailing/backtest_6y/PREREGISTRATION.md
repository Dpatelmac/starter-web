# Pre-registered test 9: the three best one-year versions over six years

Written and committed **before** `bt6y.py` was run (2026-11-04). The three
strategies are fixed exactly as chosen in the one-year test
(`../live_1y/`); nothing is re-tuned.

## Strategies (all: 12% trailing stop, risk controls on, $1,000 per trade)

Common rules: each trading day rank S&P 500 members (from their date added)
that fell 2%+ (close >= $20, volume >= 1M), biggest drop first. Skip
"explained" drops: earnings the evening before or on the drop day (Yahoo
earnings dates), or an 8%+ gap down at that morning's open. Buy at the next
open; sell only when the price falls 12% below the highest close since entry
(at the open if it opens below the stop, else at the stop when the day's low
touches it). Risk controls: at most 24 open positions, at most 2 new buys per
sector per day, no buying a stock already held or stopped out in the last 10
trading days. Costs 0.05% per side plus 0.10% on stop sales.

| # | Selection | Earnings rule |
|---|---|---|
| S1 | Top 4 after removing explained | Also skip stocks reporting in the next 10 trading days |
| S2 | Top 4 after removing explained | Skip same-day earnings only |
| S3 | First 10 losers, then remove explained | Skip same-day earnings only |

## Account and benchmark

Account: $24,000 (24 slots x $1,000), fixed $1,000 per trade (no
compounding), idle cash earns nothing (conservative). Benchmark: $24,000 in
SPY bought and held (dividends included).

## Periods

- **Unseen period (decides pass/fail): drop days 2020-11-02 to 2025-10-31.**
  The strategies were selected on 2025-11-03 to 2026-11-03.
- Full six years and each calendar year are also reported.

## Pass criteria (each strategy, unseen period)

1. Profit on the $24,000 account higher than SPY's on $24,000.
2. Sharpe ratio of the account's daily value (over T-bills) higher than SPY's.
3. Worst drawdown of the account smaller than SPY's.

Reported for context: per-year results, win rate, average win and loss,
share of profit from the top 10 trades, sector mix, and stocks that were in
the index only part of the time.

## Known limits

- Universe is today's S&P 500 members, counted from their date added; stocks
  that were removed from the index (often after big falls) are missing, which
  flatters dip buying.
- Yahoo earnings dates for older years may be incomplete; any candidate with
  no known earnings history is skipped and counted.
- After-hours moves are not counted.
