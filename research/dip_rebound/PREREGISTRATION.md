# Pre-registered holdout test: the oversold-in-a-selloff lead

Written and committed **before** any holdout prices were downloaded
(2026-11-01). The rules and pass criteria below are fixed. Results are
reported as they come out, pass or fail.

## Where the lead came from

In the S&P 500/400 backtest (`backtest.py`, 2005-2026), the plain dip signal
had no edge, and the rule picked on 2005-2015 failed on 2016-2026. Two
conditions stayed positive in both periods (3-day edge vs same-morning
stocks):

| Condition | 2005-2015 | 2016-2026 |
|---|---|---|
| Stock down 5%+ over the prior 5 days | +0.21% (t 1.90) | +0.11% (t 1.50) |
| S&P 500 down 1%+ that day | +0.08% (t 2.13) | +0.10% (t 1.85) |

These were noticed after seeing the 2016-2026 results, so that period can no
longer test them. A fresh set of stocks is needed.

## Holdout universe

US-listed stocks with market cap of $2B or more today (Nasdaq screener,
2026-11-01) that are **not** current S&P 500 or S&P 400 members: 835
tickers, `data/nasdaq_screener_2b.csv`. None of these stocks were used to
find the lead.

## Fixed rules (no changes after data is seen)

Same signal filters, timing and edge metric as `backtest.py`:

- Dip: close-to-close return <= -2%, volume >= 1M shares, unadjusted close >= $20.
- Buy at the next open, sell at the close 3 sessions later.
- Edge: signal return minus the average return of every eligible holdout
  stock over the same window; signals averaged by date before the t-stat.
- Period: 2005-01-01 to 2026-10-30, split at 2015-12-31 for a stability check.

**Primary rule (H1):** dip AND stock down 5% or more over the 5 sessions
before the dip day AND SPY down 1% or more on the dip day.

Secondary, reported for context only:

- H2: dip AND prior 5 days down 5%+ (no market condition).
- H3: dip AND SPY down 1%+ (no stock condition).
- H0: every dip (the baseline that failed before).

## Pass criteria for H1

All three must hold:

1. 3-day edge > 0 with t-stat >= 2.0 over the full holdout period.
2. Edge > 0 in both 2005-2015 and 2016-2026 (no t-stat bar per half).
3. A portfolio trading H1 (same simulator, 3-day hold, 5 bps per side)
   has a positive annual return after costs.

If H1 fails any of these, the lead is treated as not real and is not built on.

## Known biases going in

- Survivorship: the holdout is stocks that are large **today**, so it
  over-represents past winners and has no delisted names. That flatters
  every rule, including the baseline. The edge metric compares against the
  same survivor universe, which offsets part of this but not all.
- Many holdout names listed after 2005, so the early years have fewer stocks.

---

# Pre-registered test 2: a lower-turnover weekly pullback portfolio

Written and committed **before** running `weekly.py` (2026-11-01).

## Why

`sweep.py` found one pattern in all three samples: stocks down 2-5% over 5
days beat same-morning stocks over the next 3-10 days, by about 0.09% per
trade. Traded daily it loses that to costs. The user trades commission-free
with market orders, so the base cost is **5 bps per side**, also shown at 10.

## Strategy (fixed)

- Once a week: signal at the last close of the week, trade at the next open,
  hold until the following week's open.
- Candidates: same filters as before (volume >= 1M, close >= $20, in the
  universe) and 5-day return <= -2%.
- Hold the top N candidates, equal weight; empty slots stay in cash (0%).
- Costs charged on the actual turnover each week, including re-weighting.

## Variants (36, all reported)

- N: 10, 20, 50 names.
- Ranking: (a) deepest 5-day drop; (b) deepest 5-day drop between -2% and
  -10%, which leaves out crash-size moves that the sweep found don't bounce.
- Filter: none; SPY above its 200-day average (else all cash); stock above
  its own 200-day average.
- Buffer: none; or keep a holding while it still qualifies and ranks in the
  top 2N, filling only open slots (fewer trades).

## Samples and pass criteria

Samples: S&P 500/400 2005-2015, S&P 500/400 2016-2026, and the 835 new
stocks 2005-2026.

A variant **passes** only if, at 5 bps per side, in **every** sample:

1. its annual return beats SPY buy and hold over the same period, and
2. its Sharpe ratio beats SPY's over the same period.

Also reported for context: 10 bps results, max drawdown, turnover, and an
equal-weight portfolio of all eligible stocks rebalanced weekly at the same
cost. If no variant passes, the pullback idea is dropped as not tradable at
the user's costs.
