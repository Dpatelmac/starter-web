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

echo "== V1/V2 reports"
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
echo "== V3 · daily trend-strategy search (LITE 3 years) + checks on LITE 2016–2023 and peers"
DAILY=data/2026-11-03-daily
mkdir -p "$OUT/v3"
SETS=("LITE 2023-11-03 - LITE_3y" "LITE 2016-01-04 2023-11-02 LITE_oos" "COHR 2023-11-03 - COHR_3y" "AAOI 2023-11-03 - AAOI_3y" "CIEN 2023-11-03 - CIEN_3y" "NVDA 2023-11-03 - NVDA_3y")
V3SPECS="V3|sma_band|8,45,1.0|V3 · SMA 8/45, 1% band;10/45 2%|sma_band|10,45,2.0|SMA 10/45, 2% band;15/50|sma_cross|15,50|SMA 15/50 cross;Supertrend|supertrend|10,3.0|Supertrend 10/3;Donchian|donchian|20,15|Donchian 20/15"
for k in "${SETS[@]}"; do
  set -- $k
  $PY backtest_v3.py search "$DAILY" "$1" "$2" "$3" "$OUT/v3/search_$4.json" > "$OUT/v3/search_$4.txt"
  $PY backtest_v3.py report "$DAILY" "$1" "$2" "$3" "$OUT/v3/rep_$4.json" "$V3SPECS" > "$OUT/v3/rep_$4.txt"
done
$PY v3_meta.py "$DAILY" "$OUT/v3" > "$OUT/v3/meta.json"
REPORT_META="$(cat "$OUT/v3/meta.json")" $PY build_report.py report_template.html LITE_backtest_report_V3.html \
  "$OUT/v3/rep_LITE_3y.json" "LITE · 3 years" "3 years" \
  "$OUT/v3/rep_LITE_oos.json" "LITE · 2016–2023 (check)" "8 years (2016–2023)" \
  "$OUT/v3/rep_COHR_3y.json" "COHR · 3 years" "3 years" \
  "$OUT/v3/rep_AAOI_3y.json" "AAOI · 3 years" "3 years" \
  "$OUT/v3/rep_CIEN_3y.json" "CIEN · 3 years" "3 years" \
  "$OUT/v3/rep_NVDA_3y.json" "NVDA · 3 years" "3 years"
echo "done · text summaries (every trade) in $OUT/*.txt and $OUT/v3/*.txt"
