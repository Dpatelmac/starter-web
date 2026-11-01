"""Account-level check of the one pattern the sweep found in all three samples:
multi-day pullbacks (stock down X% over 3 or 5 days) bouncing over the next
3-5 sessions. Simulated with backtest.simulate at 0, 2 and 5 bps per side.
Output: results/pullback_check.json
"""
import json
from pathlib import Path
import pandas as pd
import backtest as bt
from holdout import holdout_universe

HERE = Path(__file__).resolve().parent
CASES = [("5-day drop 2%+", "ret5", 0.02, 5), ("5-day drop 3%+", "ret5", 0.03, 5), ("3-day drop 3%+", "ret3", 0.03, 5),
         ("5-day drop 2%+", "ret5", 0.02, 3)]

def events(px, etf, uni, member):
    px = bt.prepare(px, etf, uni)
    g = px.groupby("ticker", sort=False)
    px["ret3"] = px["adj_close"] / g["adj_close"].shift(3) - 1
    px["ret5"] = px["adj_close"] / g["adj_close"].shift(5) - 1
    px = px[(px["date"] >= bt.START) & px["entry"].notna() & px["r1"].notna()]
    elig = (px["volume"] >= bt.MIN_VOL) & (px["close"] >= bt.MIN_PRICE) & px["prev_aclose"].notna()
    if member: elig &= px["in_index"]
    return px, px[elig]

out = {}
spx, etf, suni = bt.load()
hpx = pd.read_parquet(HERE / "data" / "holdout_prices.parquet"); huni = holdout_universe()
for uname, (px, uni, member) in {"S&P 500/400": (spx, suni, True), "New stocks": (hpx, huni[huni.ticker.isin(hpx.ticker.unique())], False)}.items():
    p, base = events(px, etf, uni, member)
    dates = pd.DatetimeIndex(sorted(p["date"].unique())); oos = dates > bt.IS_END
    # Benchmark: equal-weight every eligible stock, same simulator (isolates the pullback filter).
    for name, col, k, hold in CASES + [("All eligible stocks (benchmark)", None, None, 5)]:
        ev = base if col is None else base[base[col] <= -k]
        per_day = ev.groupby("date").size().median()
        for c in [0, 2, 5]:
            eq = bt.simulate(ev, p, dates, hold, cost_bps=c)
            f, s = bt.perf(eq), bt.perf(eq[oos] / eq[oos].iloc[0])
            out[f"{uname} | {name} | {hold}d | {c}bps"] = {"full": f, "2016": s, "names_per_day": float(per_day)}
            print(f"{uname:<12} {name:<32} hold {hold}d {c}bps/side  names/day {per_day:5.0f} | CAGR {f['cagr']*100:5.1f}% Sharpe {f['sharpe']:.2f} maxDD {f['max_dd']*100:4.0f}% | 2016+: CAGR {s['cagr']*100:5.1f}% Sharpe {s['sharpe']:.2f}")
json.dump(out, open(HERE / "results" / "pullback_check.json", "w"), indent=1, default=float)
