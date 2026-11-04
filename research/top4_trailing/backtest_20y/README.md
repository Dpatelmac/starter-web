# Test 10: strategy S1 over twenty years (run on the Mac)

Pre-registered in `PREREGISTRATION.md` (cb583e7) before any 20-year run.
Pass/fail is decided on **2005 to Oct 2020**, which S1 has never been tested on.

## Run it (from the research folder)

```bash
cd /Users/claud/Documents/1Projects/tradingbot2/research
python3 -m pip install yfinance pandas numpy pyarrow lxml requests
python3 dip_rebound/fetch_data.py                 # 20-year prices, ~2-3 min (skip if already downloaded)
python3 top4_trailing/backtest_20y/run_20y.py     # earnings dates (~10 min first time, cached), backtest, report
open top4_trailing/backtest_20y/report.html
```

- Re-run without downloading earnings dates again: add `--skip-fetch`.
- Quick code check (2024-2026, no downloads): `--smoke`.

Outputs next to this file: `report.html` (offline, interactive),
`results.json`, `trades.csv`, `earnings_dates.json` (cache).

## What it does

S1 exactly as in tests 8-9: each day the top 4 S&P 500 losers (down 2%+, $20+,
1M+ shares) after skipping explained drops (earnings that day or the evening
before, an 8%+ opening gap, a report due in the next 10 trading days); buy at
the next open, $1,000 each; sell by a 12% trailing stop; at most 24 positions,
2 new buys per sector per day, 10-day cool-off. $24,000 account; idle cash
earns the T-bill rate (results without interest also shown). Benchmark: SPY on
$24,000.

The report shows the verdict and the three pre-registered checks, the
never-tested period and 2010-2020, five-year sub-periods, every calendar year
(with how many candidates were skipped for missing earnings history), account
value and drawdown vs SPY, and every trade.

After running, commit the results so they're saved:

```bash
cd /Users/claud/Documents/1Projects/tradingbot2-repo && cp -R ../tradingbot2/research/top4_trailing/backtest_20y/. research/top4_trailing/backtest_20y/ && git add research/top4_trailing/backtest_20y && git commit -m "Test 10 results: S1 over twenty years" && git push origin pullback_research
```
