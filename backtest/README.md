# LITE strategy backtests

Offline, self-contained HTML reports (open in any browser, no internet needed):

| Report | What it covers |
|---|---|
| `LITE_backtest_report.html` | V1, past 1 month, 1D → 2m bars |
| `LITE_backtest_report_6M.html` | V1, past 6 months, 1D/4H/2H/1H |
| `LITE_backtest_report_4Y.html` | V1 Dollar vs Percent mode, 4 years daily + Dec 2023 → now intraday |
| `LITE_backtest_report_V2.html` | **V2** (trend filter, 3% / 5% tight trail) vs V1, 1D 4 years + 4H/2H/1H since Dec 2023 |

Pine scripts: `../pinescript/lite_dip_rebound_two_stage_trail.pine` (V1) and
`../pinescript/lite_dip_rebound_two_stage_trail_v2.pine` (V2).

## Regenerating

Data comes from Yahoo Finance chart JSON (`LITE_1d.json`, `LITE_1h.json`, ... in one folder; regular hours only).
Yahoo serves 1h bars for the last ~730 days and 30m and shorter for the last 60 days.

```bash
# V1: <data_dir> <start> <out.json> <tf[:mode],...>   mode: $ (default) or %
python3 backtest.py data 2022-11-03 r4y.json "1D:\$,1D:%"

# V2: <data_dir> <start> <out.json> "key|bar|mode|trend 0/1|tight override|name;..."
python3 backtest_v2.py data 2023-12-06 v2_4H.json "V1 %|4H|%|0||V1 · Percent, 1% trail;3%|4H|%|0|3|V2 · 3% trail"

# Report: <template> <out.html> then one or more "<results.json> <window label> <period text>"
REPORT_META='{"title":"LITE · Dip-Rebound Strategy V2","baseline":"V1 %"}' \
  python3 build_report.py report_template.html out.html v2_4H.json "4H · Dec 2023 → now" "2 years 11 months"
```

These are simulations of the Pine logic with TradingView-style fills (signals at bar close, entries at the next
open, stops at the stop price or the open on a gap). They are not TradingView's own Strategy Tester and not
investment advice.
