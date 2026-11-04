# 3-month ledger: top 4 unexplained S&P 500 losers, trailing stop

Illustration over drop days 2026-08-06 to 2026-11-03 (63 trading days),
positions marked at the 2026-11-04 close. Not pre-registered; no trades sent.

```bash
python3 ledger3m.py      # uses prices.parquet + earnings_dates.json (cached); writes data.json, CSVs
python3 build_report.py  # writes report.html (offline, self-contained)
```

Switches in the report: selection (top 4 after removing explained, or first
10 then remove), trailing stop (8% or 3%), earnings rule (skip same-day only,
or also skip stocks reporting in the next 10 days).

Files: `trades_<stop>_<earnings>_<selection>.csv` (every trade),
`candidates_<selection>_<earnings>.csv` (every loser checked and why it was
bought or skipped), `data.json` (report data), `prices.parquet` (Yahoo daily
bars from 2026-07-01), `earnings_dates.json` (Yahoo earnings dates).

Results and caveats: see `research/SUMMARY.md` ("Live ledgers").
