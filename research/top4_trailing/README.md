# Test 8: top 4 of the 10 biggest S&P 500 decliners, trailing-stop exits

Pre-registered in `PREREGISTRATION.md` (e0569b2). Run: `python3 top4.py`
(about 2.5 minutes) -> `results/top4.json`, `results/trades_primary.csv`.

Each day: the 10 biggest S&P 500 decliners (down 2%+); skip any that open
+1.5% or more next morning; buy the 4 with the deepest next-open gap at the
open; 2% of equity each, at most 50 positions; exit only by trailing stop
(open below the stop -> sell at open; low touches it -> sell at the stop).
Costs 5 bps per side plus 10 bps on stop sales; cash earns T-bills.

## Result: primary (3% trailing stop) FAILS

| Sample | CAGR | Sharpe | Worst fall | Months + | Win rate | Avg win / loss | Days held | Invested |
|---|---|---|---|---|---|---|---|---|
| S&P 500 2005-15 | -0.3% | -0.23 | -17% | 50% | 34.5% | +4.6% / -2.5% | 7.3 | 41% |
| S&P 500 2016-26 | 3.4% | 0.20 | -7% | 53% | 35.9% | +4.9% / -2.6% | 6.7 | 41% |
| S&P 400 2005-26 | 0.9% | -0.18 | -14% | 52% | 34.2% | +5.0% / -2.6% | 5.0 | 18% |
| New stocks 2005-26 | -0.9% | -0.56 | -25% | 46% | 31.2% | +5.5% / -2.8% | 4.1 | 17% |
| SPY buy & hold | 7.1% / 14.8% / 10.8% | 0.38 / 0.74 / 0.54 | -55% / -34% / -55% | | | | | |

It has a much smaller worst fall than SPY in every sample, but makes little
or no money: about two trades in three lose. A 3% stop is inside a beaten-down
stock's normal daily swing, so 15-31% of trades are stopped out on the day
they are bought. Worst falls are small mainly because only 17-41% of the
account is invested at a time. It beats random picks from the same top 10 in
every sample, but by little (Sharpe 0.20 vs 0.08 in 2016-26).

## Other trailing stops (reported, not used to pass)

| Trail | S&P 500 2005-15 | S&P 500 2016-26 | S&P 400 | New stocks |
|---|---|---|---|---|
| 5% | 2.6% / 0.17 / -31% | 7.1% / 0.49 / -15% | 1.9% / 0.05 / -17% | -0.3% / -0.21 / -28% |
| **8%** | 5.1% / 0.33 / -42% | **11.8% / 0.72 / -17%** | 4.3% / 0.26 / -31% | 1.3% / 0.04 / -39% |
| 2x ATR | 0.2% / 0.04 / -62% | 15.8% / 0.80 / -26% | 6.4% / 0.37 / -40% | 4.1% / 0.21 / -55% |
| Random 4 picks, 8% trail | 5.0% / 0.32 / -43% | 10.6% / 0.66 / -20% | 4.4% / 0.27 / -32% | 0.5% / -0.03 / -39% |

(CAGR / Sharpe / worst fall.) Wider stops keep the account more invested
(67-90%) and do better, but they behave like the market itself: random picks
from the same top 10 do almost as well, so the ranking adds little, and
none beats SPY's Sharpe outside S&P 500 2016-26. The 8% stop's 2016-26 result
(Sharpe 0.72 vs SPY 0.74, half the worst fall) is the best-looking cell but
fails every other sample.

## Conclusion

Trailing stops cut drawdowns, mainly by keeping money in cash, but don't
create an edge. Win rates are low (31-40%), as is normal for trailing-stop
systems, so profit depends on big winners, which this setup doesn't produce
reliably. Recommendation unchanged: hold, no trades.
