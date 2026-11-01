# Regime-gated momentum proposal (pre-registered test 3)

Proposal reviewed against the SIGNUM/IBKR paper portfolio and current market
(`snapshot.py`), then tested with rules and pass criteria committed in
`PREREGISTRATION.md` before any run (`momentum.py`).

```bash
python snapshot.py   # portfolio + market snapshot (needs ../dip_rebound/data from fetch_data.py)
python momentum.py   # backtest, ablations, benchmarks, today's target portfolio
```

## Result: FAIL, so no change is recommended

Full strategy (D) at 5 bps per side, against SPY buy and hold:

| Sample | Strategy CAGR / Sharpe / max fall | SPY CAGR / Sharpe / max fall | Sharpe beats SPY | Smaller max fall |
|---|---|---|---|---|
| S&P 2005-15 | 9.2% / 0.60 / -17% | 7.1% / 0.38 / -55% | yes | yes |
| S&P 2016-26 | 5.1% / 0.26 / -32% | 14.8% / 0.74 / -34% | **no** | yes |
| New stocks 2005-26 | 3.5% / 0.19 / -40% | 10.8% / 0.54 / -55% | **no** | yes |

It fails criterion 1 in two of three samples. Over 2016-2026 it trailed
SPY by about 10 points a year.

What the ablations show (all verified in this run):

- Plain top-20 momentum (A) did well after 2016 (18.4% a year) but fell 42-63%
  in drawdowns and lost to SPY in the other two samples.
- Each risk layer (regime switch, inverse-vol sizing, volatility target, loss
  limit) cut drawdowns but cost more return than it saved in risk after 2016.
- **Momentum stock selection added nothing beyond the regime switch itself:**
  SPY with the same 200-day switch beat every momentum version on Sharpe in
  every sample.

SPY with the 200-day switch (benchmark, not the pre-registered strategy):

| Sample | CAGR | Sharpe | Max fall |
|---|---|---|---|
| S&P 2005-15 window | 9.9% | 0.72 | -17% |
| S&P 2016-26 window | 9.1% | 0.58 | -24% |
| Full 2005-26 | 9.5% | 0.65 | -24% |

It cut the worst fall by more than half in every window but gave up 5.7
points a year in 2016-2026, a strong bull market with sharp, quick dips.
This is a lead for a future pre-registered test, not a verified result: it
was a benchmark here, it was seen before being tested, and the simulator
trades it at the prior close (a small simplification).

## Flaw found in the design

Inverse-volatility sizing gave the largest weight (6.6%) to LNTH, whose 60-day
volatility is only 3.9%, typical of a stock pinned by a pending acquisition.
Low-volatility sizing should exclude such stocks. This was not changed after
the fact; it is noted for any future version.

## Recommendation (for review, no trades)

- Do not adopt the momentum strategy.
- Make no trades on its basis. The target list in
  `results/target_portfolio.csv` is shown only for transparency.
- Portfolio risk worth reviewing separately: the stock sleeve is 63%
  chips/tech with a beta of 2.15, and the bot has logged no activity since
  2026-10-14.
