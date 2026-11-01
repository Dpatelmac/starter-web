# Pre-registered test 3: regime-gated, risk-budgeted momentum

Written and committed **before** `momentum.py` was run (2026-11-01). Rules,
parameters and pass criteria are fixed. Every parameter is a standard
textbook value, not tuned on this data.

## Context (snapshot.py, close of 2026-10-30)

- Paper portfolio (IBKR via SIGNUM, TR-GC-Stocks-4): NAV $23,941, 64% cash.
  The stock sleeve is 63% chips/tech, beta 2.15 vs SPY, 34% annualized
  volatility, position sizes from 0.9% to 5.4% of NAV. No trades since
  2026-10-14.
- Market: SPY 4.1% above its 200-day average, 3% below its high; tech
  (XLK) -9.3% in October; health care, energy and staples at highs; VIX 19.4;
  57% of S&P 500/400 stocks above their 200-day average; T-bills 3.97%.

## The strategy

| | Rule |
|---|---|
| Universe | S&P 500 + S&P 400 members (from the date each joined, where known), close >= $20, 20-day average volume >= 1M shares |
| Horizon | Monthly rebalance; positions typically held 1-6 months |
| Signal | 12-1 month momentum: return from 252 to 21 trading days ago |
| Entry | At the last close of each month, rank by momentum; trade at the next open. Hold the top 20, at most 5 per sector |
| Exit | A holding is sold when it falls out of the top 40 at a monthly rebalance (keeps turnover down), or by the regime or loss rules below |
| Sizing | Inverse 60-day volatility, capped at 10% per name, then scaled so forecast portfolio volatility is 15% a year (never above 100% invested, no leverage) |
| Market regime | Invest only if SPY closes above its 200-day average at month-end; otherwise hold T-bills |
| Maximum loss | If the strategy falls 20% below its peak, sell everything at the next open and hold T-bills until the next month-end with the regime on (peak then resets) |
| Costs | 5 bps per side on all traded value (commission-free market orders); 10 bps stress test. Cash earns the 13-week T-bill yield (^IRX) |

## Samples

S&P 500/400 2005-2015, S&P 500/400 2016-2026, and the 835 US stocks over
$2B outside the S&P 500/400 (2005-2026), with SPY's 200-day regime.

## Pass criteria (at 5 bps per side, in all three samples)

1. Sharpe ratio (on returns above T-bills) higher than SPY buy and hold.
2. Maximum drawdown smaller than SPY buy and hold's.
3. Annual return above the T-bill return.

Annual return above SPY is reported but **not** required: the aim is
risk-adjusted return.

## Reported for context (not used to choose anything)

- Ablations: (A) plain top-20 momentum, equal weight, always invested;
  (B) A + regime switch; (C) B + inverse-vol sizing, sector cap and buffer;
  (D) the full strategy (C + volatility target + loss limit).
- SPY with the same 200-day regime switch (tests whether stock selection adds
  anything beyond timing the index).
- Equal-weight all eligible stocks, rebalanced monthly.
- 10 bps per side results and yearly turnover.

## What would invalidate it

- Momentum crashes: sharp reversals when beaten-down stocks rebound (2009,
  late 2020). The regime switch and loss limit are meant to limit, not
  prevent, these.
- Choppy markets around the 200-day average cause whipsaw trades.
- Survivorship: delisted stocks are missing. Momentum buys recent winners,
  which delist less often than losers, so the bias should be smaller than in
  the dip tests, but it still flatters results.

## Decision rule

If it passes, propose it for paper trading with today's target portfolio,
for review only. If it fails, recommend no change.
