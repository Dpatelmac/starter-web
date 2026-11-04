# Pre-registered test 7: the user's pullback framework (v6)

Written and committed **before** `v6.py` was run (2026-11-04). Thresholds
come from the user's guideline; nothing was tuned on this data.

## Base signal (unchanged)

Day t: close-to-close return <= -2%, volume >= 1M shares, close >= $20, in
the universe. Entry at the open of t+1 (the trader sees the open print; using
the open price is slightly optimistic, so costs are stressed up to 20 bps).
Exit at the close of t+h; primary hold h = 3 days (1, 2, 5 reported).

## Step 1: ignore list (skip if any is true)

| Id | Rule | Definition |
|---|---|---|
| I1 | News gap down | drop-day open <= -8% vs prior close |
| I2 | Already bounced | close in the upper half of the day's range |
| I3 | Bounce priced next morning | next open >= +1.5% vs drop-day close |
| I4 | Sector being re-rated | stock's sector ETF down 3 days in a row (t, t-1, t-2); SPY when no sector ETF |

Not testable with daily prices (kept as live rules for the evening research
step): SEC filings (424B, 8-K 4.02/1.02, NT 10-Q), analyst pile-on, earnings
or scheduled events inside the hold.

## Step 2: bounce signals (score = how many are true, 0-7)

| Id | Signal | Definition |
|---|---|---|
| S1 | Opened flat, sold off all day | drop-day open > -1% |
| S2 | Closed at the low | close in the bottom 25% of the day's range |
| S3 | Extremely oversold | RSI(2) < 5, or close <= 10-day high - 3 x ATR(14) |
| S4 | Climax volume | volume >= 3x its 20-day average |
| S5 | Market-wide selloff | SPY down 1% or more on day t |
| S6 | No stock-specific damage | return minus beta x SPY return > -3% (beta: prior 60 days) |
| S7 | Final flush | next open <= -3% vs drop-day close |

Not testable here (no 20-year history available): earnings surprise and
guidance, short interest, put volume / implied volatility, insider buying and
buybacks.

## Candidate rules (all three reported; no picking afterwards)

- **R_A (framework):** passes the ignore list AND score >= 3.
- **R_B (final flush):** passes the ignore list AND S7.
- **R_C (both):** passes the ignore list AND score >= 3 AND S7.

## Samples

S&P 500/400 2005-2015, S&P 500/400 2016-2026, and the 835 US stocks over $2B
outside the S&P 500/400 (2005-2026).

## Pass criteria (each rule, 3-day hold, 5 bps per side, in ALL three samples)

1. Edge vs stocks bought the same morning >= +0.10% per trade (covers the
   round trip) with t-stat >= 2.
2. Portfolio Sharpe higher than SPY buy and hold over the same period.
3. Portfolio maximum drawdown smaller than SPY's.

Portfolio: each signal gets at most 10% of a sleeve (rest in cash), rolling
sleeves as in `dip_rebound/backtest.py`. Also reported: trade win rate, months
positive, 10 and 20 bps costs, the marginal effect of each ignore rule and each
signal, and the edge by score (a working framework should rise with score in
every sample).

## Expectation stated in advance

A "100x better" result is not a realistic target. A pass here would mean a
modest, cost-surviving edge; a fail means the price-based parts of the
framework don't add one, and its value would have to come from the news-based
checks.
