# One-year test: top 4 unexplained S&P 500 losers, trailing stop, 32 versions

Drop days 2025-11-03 to 2026-11-03 (252 trading days), open positions marked
at the 2026-11-04 close. Not pre-registered; no trades sent.

```bash
python3 ledger_1y.py      # ~4 min; uses prices.parquet and earnings_dates.json (cached)
python3 build_report.py   # report.html (offline, self-contained, ~7 MB)
```

Versions: selection (top 4 after removing explained / first 10 then remove)
x earnings (skip same-day / also skip stocks reporting in the next 10 days)
x stop (3/5/8/12%) x risk controls (off / max 24 positions, max 2 new buys per
sector per day, no re-buy within 10 days of a stop-out, no doubling up).

## Best runnable version

12% stop, top 4 after removing explained, skip upcoming earnings, risk
controls on: **+$7,821** on $24,000 peak capital (+32.6%) vs SPY on the same
capital +$3,513 (+14.6%); worst drawdown -$2,411 (-10.0%) vs SPY -8.9%; both
halves positive (+$4,555 / +$3,265); 10 of 13 months up; 43% winning trades,
average win +19% vs loss -8%.

**Caveats:** best of 32 on one rising year; 90% of its profit came from 10 of
221 trades (MU +119%, LITE +105%, VLO +76%); tech-heavy; current S&P 500
members only; after-hours moves not counted. The 20-year test of the same idea
with an 8% stop (`../top4.py`, test 8) roughly tracked the market. Next:
pre-register this version and test it over 20 years, then paper-trade it.

Files: `versions.csv` (all 32 versions), `trades_*.csv` (8%/12% "after"
versions), `data.json`, `prices.parquet`, `earnings_dates.json`.
