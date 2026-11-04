"""Download S&P 500 daily prices from 2020 and earnings dates back to 2019."""
import json, time
from pathlib import Path
import pandas as pd, yfinance as yf
HERE = Path(__file__).resolve().parent
u = pd.read_csv(HERE.parent.parent / "dip_rebound/data/universe.csv")
sp = u[u["index"] == "SP500"]["ticker"].tolist()
if not (HERE / "prices.parquet").exists():
    d = yf.download(sp + ["SPY"], start="2020-06-01", auto_adjust=False, group_by="ticker", threads=True, progress=False)
    long = d.stack(level=0, future_stack=True).rename_axis(["date", "ticker"]).reset_index()
    long.columns = [str(c).lower().replace(" ", "_") for c in long.columns]
    long.dropna(subset=["close"]).to_parquet(HERE / "prices.parquet", index=False)
cache = HERE / "earnings_dates.json"
earn = json.loads(cache.read_text()) if cache.exists() else {}
todo = [t for t in sp if t not in earn or not earn[t] or min(earn[t]) > "2020-10-01"]
for i, t in enumerate(todo):
    for attempt in range(3):
        try:
            e = yf.Ticker(t).get_earnings_dates(limit=40)
            earn[t] = sorted({str(pd.Timestamp(x).tz_localize(None).date()) for x in e.index}) if e is not None and len(e) else None
            break
        except Exception as ex:
            time.sleep(2 * (attempt + 1)); earn[t] = None
    if i % 50 == 0:
        cache.write_text(json.dumps(earn)); print(f"  {i}/{len(todo)}", flush=True)
cache.write_text(json.dumps(earn))
ok = [t for t in sp if earn.get(t)]
early = [t for t in ok if min(earn[t]) <= "2020-10-31"]
print(f"earnings: {len(ok)}/{len(sp)} tickers with dates, {len(early)} reaching back to Oct 2020; none: {[t for t in sp if not earn.get(t)][:20]}")
