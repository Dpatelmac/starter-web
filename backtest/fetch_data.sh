#!/usr/bin/env bash
# Download a fresh Yahoo Finance snapshot for one symbol into backtest/data/<YYYY-MM-DD>/{1m,6m,4y,v2}.
# usage: bash backtest/fetch_data.sh [SYMBOL]      (default LITE)
# Yahoo limits: 1d any range · 1h last ~730 days · 30m/15m/5m/2m last 60 days · 1m last 7 days.
# Regular trading hours only (includePrePost=false). A browser-like User-Agent is required.
set -euo pipefail
cd "$(dirname "$0")"
SYM="${1:-LITE}"
DAY=$(date +%F); [ -e "data/$DAY" ] && DAY="$DAY-$(date +%H%M)"   # never overwrite an existing snapshot
BASE="https://query1.finance.yahoo.com/v8/finance/chart/$SYM"
UA="Mozilla/5.0"
get() { curl -sS -A "$UA" -o "$1" "$2"; python3 -I -c "import json,sys; r=json.load(open(sys.argv[1]))['chart']; assert r['result'], r['error']; print(sys.argv[1], len(r['result'][0]['timestamp']), 'bars')" "$1"; }
D="data/$DAY"; mkdir -p "$D/1m" "$D/6m" "$D/4y" "$D/v2"

# 1-month set (intraday down to 2m)
get "$D/1m/${SYM}_1d.json"  "$BASE?range=3mo&interval=1d&includePrePost=false"
get "$D/1m/${SYM}_1h.json"  "$BASE?range=2mo&interval=1h&includePrePost=false"
for iv in 30m 15m 5m 2m; do get "$D/1m/${SYM}_$iv.json" "$BASE?range=1mo&interval=$iv&includePrePost=false"; done
get "$D/1m/${SYM}_1m.json"  "$BASE?range=7d&interval=1m&includePrePost=false"
# 6-month set
get "$D/6m/${SYM}_1d.json"  "$BASE?range=1y&interval=1d&includePrePost=false"
get "$D/6m/${SYM}_1h.json"  "$BASE?range=1y&interval=1h&includePrePost=false"
# 4-year set (daily) + max hourly
get "$D/4y/${SYM}_1d.json"  "$BASE?range=5y&interval=1d&includePrePost=false"
get "$D/4y/${SYM}_1h.json"  "$BASE?range=730d&interval=1h&includePrePost=false"
# V2 set: extra daily history so the 200-day average is warm at the start of the 4-year window
get "$D/v2/${SYM}_1d.json"  "$BASE?range=10y&interval=1d&includePrePost=false"
cp "$D/4y/${SYM}_1h.json" "$D/v2/${SYM}_1h.json"
echo "snapshot in backtest/$D · note: backtest.py reads files named LITE_<iv>.json; for another symbol rename or adapt load()."
