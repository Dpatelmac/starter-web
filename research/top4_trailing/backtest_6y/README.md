# Test 9: the three best one-year versions over six years (pre-registered)

Rules and pass marks committed in `PREREGISTRATION.md` (24c0977) before the
run. Drop days 2020-11-02 to 2026-11-03; $24,000 account, $1,000 per trade,
at most 24 positions, 12% trailing stop.

```bash
python3 fetch6y.py        # prices from 2020-06 + Yahoo earnings dates (cached; ~6 min first time)
python3 bt6y.py           # results.json, trades_S1/S2/S3.csv
python3 build_report.py   # report.html (offline, interactive)
```

## Result on the unseen five years (Nov 2020 - Oct 2025)

| | Profit on $24k | Per year | Sharpe | Worst drawdown | Verdict |
|---|---|---|---|---|---|
| SPY buy & hold | $28,452 (+117.7%) | 16.9% | 0.82 | -24.5% | |
| **S1** top 4 after removing explained + skip upcoming earnings | **$29,161 (+121.3%)** | 17.2% | **0.95** | **-20.4%** | **PASS** |
| S2 top 4 after removing explained | $26,541 (+110.4%) | 16.1% | 0.87 | -20.7% | FAIL (less profit) |
| S3 first 10 losers, then remove explained | $23,396 (+97.3%) | 14.6% | 0.78 | -22.1% | FAIL |

S1 passes all three checks but beats SPY's profit by only $709 over five
years; its clearer edge is risk (higher Sharpe, smaller drawdown, much better
2022: -$2,427 vs SPY -$6,520). It lagged SPY in 2021, 2023 and 2026.

Full six years: S1 $33,507 vs SPY $35,629 (Sharpe 0.89 vs 0.81, drawdown
-20.4% vs -24.5%). 45% winning trades, average win +20% vs loss -8%; the top
10 trades were 34% of profit.

Limits: today's S&P 500 members counted from their date added (removed stocks
missing, which flatters dip buying); idle cash earns nothing; after-hours
moves not counted; Yahoo earnings dates (candidates without history skipped:
1-2 per strategy).
