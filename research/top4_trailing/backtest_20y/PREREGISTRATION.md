# Pre-registered test 10: strategy S1 over twenty years

Written and committed **before** any 20-year run (2026-11-04). S1 is fixed
exactly as in tests 8-9 (`../backtest_6y/`); nothing is re-tuned. The run
happens on the user's Mac with `run_20y.py`.

## Strategy S1 (unchanged)

Each trading day rank S&P 500 members (from their date added) that fell 2%+
(close >= $20, volume >= 1M), biggest drop first. Skip explained drops:
earnings the evening before or on the drop day, an 8%+ gap down at that
morning's open, or a report due in the next 10 trading days (Yahoo earnings
dates). Buy up to 4 at the next open, $1,000 each. Sell only when the price
falls 12% below the highest close since entry (at the open if it opens below
the stop, else at the stop when the day's low touches it). Risk controls: at
most 24 open positions, at most 2 new buys per sector per day, no buying a
stock already held or stopped out in the last 10 trading days. Costs 0.05%
per side plus 0.10% on stop sales.

## Account and benchmark

$24,000 account, fixed $1,000 per trade (no compounding). **Idle cash earns
the 13-week T-bill rate (^IRX)**, as planned after test 9; results without
interest are also reported. Benchmark: $24,000 in SPY bought and held
(dividends included).

## Periods

- **Never-tested period (decides pass/fail): drop days 2005-01-03 to
  2020-10-30.** S1 was chosen on 2025-11 to 2026-11 and checked on 2020-11 to
  2025-10; these 15+ years were never used.
- Also reported: full 2005-2026; 2005-2009 (incl. 2008), 2010-2014,
  2015-2019, 2020-2026; each calendar year.

## Pass criteria (never-tested period, with T-bill interest)

1. Profit on the $24,000 account higher than SPY's on $24,000.
2. Sharpe ratio of the account's daily value (over T-bills) higher than SPY's.
3. Worst drawdown smaller than SPY's.

## Data-quality rule (stated in advance)

Yahoo earnings history may not reach back to 2005 for every stock. A candidate
dropping before its first known earnings date (minus 100 days) is skipped and
counted. If more than 30% of otherwise-eligible candidates in any calendar
year are skipped for this reason, that year is flagged as unreliable in the
report, and the verdict is also shown for 2010-2020 only.

## Known limits

- Universe is today's S&P 500 members counted from their date added; stocks
  removed from the index (often after big falls, including in 2008) are
  missing. Over 20 years this survivorship bias is larger than in test 9 and
  flatters dip buying.
- After-hours moves not counted; gains would be short-term for tax.
