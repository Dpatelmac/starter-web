#!/usr/bin/env bash
# Re-run every backtest and rebuild every HTML report from a data snapshot.
# usage: bash backtest/rebuild_all.sh [snapshot_dir]   (default: backtest/data/2026-11-03)
# Needs only Python 3.9+ (standard library). Results JSON go to backtest/results/ (git-ignored).
set -euo pipefail
cd "$(dirname "$0")"
SNAP="${1:-data/2026-11-03}"
OUT=results
mkdir -p "$OUT"
PY="python3 -I"

echo "== V1 · 1 month (1D → 2m)"
$PY backtest.py "$SNAP/1m" 2026-10-03 "$OUT/v1_1m.json" 1D,4H,1H,30m,15m,5m,2m > "$OUT/v1_1m.txt"
echo "== V1 · 6 months (1D/4H/2H/1H)"
$PY backtest.py "$SNAP/6m" 2026-05-03 "$OUT/v1_6m.json" 1D,4H,2H,1H > "$OUT/v1_6m.txt"
echo "== V1 · 4 years, Dollar vs Percent"
$PY backtest.py "$SNAP/4y" 2022-11-03 "$OUT/v1_4y_daily.json" '1D:$,1D:%' > "$OUT/v1_4y_daily.txt"
$PY backtest.py "$SNAP/4y" 2023-12-06 "$OUT/v1_4y_intraday.json" '1D:$,1D:%,4H:$,4H:%,2H:$,2H:%,1H:$,1H:%' > "$OUT/v1_4y_intraday.txt"

echo "== V2 · trend filter / wider trail vs V1"
specs() {
  local b=$1
  echo "V1 \$|$b|\$|0||V1 · Dollar (original);V1 %|$b|%|0||V1 · Percent, 1% trail;Trend|$b|%|1||V2 · Trend filter, 1% trail;3%|$b|%|0|3|V2 · 3% trail;5%|$b|%|0|5|V2 · 5% trail;Trend+3%|$b|%|1|3|V2 · Trend filter + 3% trail;Trend+5%|$b|%|1|5|V2 · Trend filter + 5% trail"
}
$PY backtest_v2.py "$SNAP/v2" 2022-11-03 "$OUT/v2_1D.json" "$(specs 1D)" > "$OUT/v2_1D.txt"
for b in 4H 2H 1H; do
  $PY backtest_v2.py "$SNAP/v2" 2023-12-06 "$OUT/v2_$b.json" "$(specs $b)" > "$OUT/v2_$b.txt"
done

echo "== Reports"
$PY build_report.py report_template.html LITE_backtest_report.html "$OUT/v1_1m.json" "1 month" "month"
$PY build_report.py report_template.html LITE_backtest_report_6M.html "$OUT/v1_6m.json" "6 months" "6 months"
$PY build_report.py report_template.html LITE_backtest_report_4Y.html \
  "$OUT/v1_4y_daily.json" "4 years · Daily" "4 years" \
  "$OUT/v1_4y_intraday.json" "Dec 2023 → now · Daily + intraday" "2 years 11 months"
REPORT_META='{"title":"LITE · Dip-Rebound Strategy V2","noteTitle":"What V2 changes: ","note":"(1) Trend filter: a buy is only allowed when the bar closes above the average of the previous 200 daily closes; while below it, the strategy keeps tracking the low and buys on the first bar that qualifies. (2) Wider tight trail: 3% or 5% instead of 1% after the +6% target is reached. V2 versions use Percent mode; the two V1 versions are included unchanged as the baseline. The 200-day average uses official daily closes, which needs about 200 trading days of history before each window starts.","baseline":"V1 %"}' \
$PY build_report.py report_template.html LITE_backtest_report_V2.html \
  "$OUT/v2_1D.json" "1D · 4 years" "4 years" \
  "$OUT/v2_4H.json" "4H · Dec 2023 → now" "2 years 11 months" \
  "$OUT/v2_2H.json" "2H · Dec 2023 → now" "2 years 11 months" \
  "$OUT/v2_1H.json" "1H · Dec 2023 → now" "2 years 11 months"
echo "done · text summaries (every trade) in $OUT/*.txt"
