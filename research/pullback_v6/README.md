# Test 7: the user's pullback framework (v6), pre-registered

Rules and pass marks committed in `PREREGISTRATION.md` (f9d867e) before the
run. Run: `python3 v6.py` -> `results/v6.json`.

## Result: all three rules FAIL

3-day hold, 5 bps per side, edge vs stocks bought the same morning; portfolio
gives each signal at most 10% of a sleeve (rest in T-bills).

| Rule | Sample | Signals | Edge (t) | Winning trades | Portfolio CAGR / Sharpe / worst fall |
|---|---|---|---|---|---|
| R_A ignore + score >= 3 | S&P 2005-15 | 28,595 | +0.01% (0.21) | 51.8% | 1.4% / 0.07 / -28% |
| | S&P 2016-26 | 53,843 | -0.02% (-0.51) | 52.4% | 2.9% / 0.11 / -25% |
| | New stocks | 22,764 | +0.02% (0.31) | 50.7% | -0.7% / -0.15 / -43% |
| R_B ignore + final flush | S&P 2005-15 | 950 | **+0.85% (2.96)** | 64.6% | 3.1% / 0.35 / -9% |
| | S&P 2016-26 | 3,264 | +0.17% (0.66) | 47.0% | 2.9% / 0.13 / -12% |
| | New stocks | 2,466 | +0.28% (1.00) | 53.1% | 2.7% / 0.17 / -18% |
| R_C both | S&P 2005-15 | 861 | +0.46% (1.27) | 65.5% | 2.9% / 0.33 / -7% |
| | S&P 2016-26 | 2,817 | +0.03% (0.09) | 45.4% | 1.9% / -0.05 / -12% |
| | New stocks | 1,951 | +0.19% (0.61) | 52.7% | 2.1% / 0.08 / -18% |
| SPY buy & hold | 2005-15 / 2016-26 / full | | | | 7.1% / 0.38 / -55%; 14.8% / 0.74 / -34%; 10.8% / 0.54 / -55% |

Every rule has a smaller worst fall than SPY, but only because it sits in cash
most of the time. None beats SPY's Sharpe in any sample, and none has a
cost-covering, significant edge in all three samples.

## What each piece adds (3-day edge when the condition is true)

- **S7 final flush (next open -3% or worse)** is the only signal positive in
  all three samples: +0.93% (t 3.3), +0.36% (t 1.6), +0.31% (t 1.3). It is
  strong before 2016 and weak since, with raw returns negative after 2016
  (-0.43% for R_B).
- **S5 market-wide selloff** helps on S&P stocks (t 2.1, 1.9) but not on new
  stocks (t 0.2).
- **The score does not rise with the number of signals** in any sample, so
  adding signals together doesn't help. S1 (opened flat), S2 (closed at the
  low), S3 (RSI/ATR oversold), S4 (climax volume) and S6 (beta-adjusted drop)
  show no consistent edge.
- **Ignore rules:** I3 (skip if next open +1.5%) helps only in 2005-15; I1,
  I2 and I4 (sector down 3 days) show no consistent effect.

## Not tested (no 20-year history available here)

SEC filings, analyst pile-ons, earnings surprise and guidance, short interest,
options activity, insider buying and buybacks, the earnings calendar. These
can only be judged with a forward log of live candidates (see SUMMARY.md).

## Conclusion

The price-based parts of the framework do not produce a tradable edge. The
"final flush" signal is worth watching, but it has weakened since 2016 and
does not pass. Recommendation unchanged: hold, no trades.
