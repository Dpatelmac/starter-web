"""Two-week ledger: each day's 4 biggest S&P 500 losers with no obvious
explanation, bought at the next open, sold by trailing stop.

Illustration only (10 trading days), not a test of the strategy.
"No explanation" = no earnings report the evening before or on the drop day
(Yahoo earnings dates) and no 8%+ gap down at that morning's open. Analyst
actions and other news were not checked.

  python ledger.py   (after downloading prices_recent.parquet)
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

HERE = Path(__file__).resolve().parent
COST, STOP_SLIP, POS = 5 / 1e4, 10 / 1e4, 1000.0
N_DROP_DAYS = 10

px = pd.read_parquet(HERE / "prices_recent.parquet")
px["date"] = pd.to_datetime(px["date"])
px = px.sort_values(["ticker", "date"])
f = px["adj_close"] / px["close"]
for c in ("open", "high", "low"):
    px["a" + c] = px[c] * f
px["prev"] = px.groupby("ticker")["adj_close"].shift(1)
px["ret"] = px["adj_close"] / px["prev"] - 1
px["gap"] = px["aopen"] / px["prev"] - 1
W = lambda c: px.pivot(index="date", columns="ticker", values=c)
C, O, H, L, R, G, V, RAW = W("adj_close"), W("aopen"), W("ahigh"), W("alow"), W("ret"), W("gap"), W("volume"), W("close")
dates = C.index
last = dates[-1]
drop_days = list(dates[-N_DROP_DAYS - 1:-1])

# Top-10 decliners per drop day (S&P 500, close >= $20, volume >= 1M, down 2%+).
cands = {}
for d in drop_days:
    r = R.loc[d].drop("SPY", errors="ignore")
    ok = (RAW.loc[d] >= 20) & (V.loc[d] >= 1e6) & (r <= -0.02)
    cands[d] = r[ok.reindex(r.index).fillna(False)].sort_values().head(10)

# Earnings dates for every candidate.
tick = sorted({t for s in cands.values() for t in s.index})
earn = {}
for t in tick:
    try:
        e = yf.Ticker(t).get_earnings_dates(limit=12)
        earn[t] = sorted({pd.Timestamp(x).tz_localize(None).normalize() for x in e.index}) if e is not None else []
    except Exception:
        earn[t] = None
json.dump({t: [str(x.date()) for x in v] if v is not None else None for t, v in earn.items()}, open(HERE / "earnings_dates.json", "w"), indent=1)


def explained(t, d):
    prev_day = dates[dates.get_loc(d) - 1]
    why = []
    ed = earn.get(t)
    if ed is None:
        why.append("earnings date unknown")
    elif any(x in (prev_day, d) for x in ed):
        why.append("earnings")
    if G.at[d, t] <= -0.08:
        why.append(f"gapped {G.at[d, t]*100:.1f}% at open")
    return why


picks_rows = []
for d in drop_days:
    nxt = dates[dates.get_loc(d) + 1]
    keep = []
    for t, r in cands[d].items():
        why = explained(t, d)
        picks_rows.append({"drop_day": d.date(), "ticker": t, "drop": r, "reason_excluded": "; ".join(why) if why else ""})
        if not why and len(keep) < 4:
            keep.append(t)
    for t in keep:
        next(x for x in picks_rows if x["drop_day"] == d.date() and x["ticker"] == t)["picked"] = True
    cands[d] = (keep, nxt)
pd.DataFrame(picks_rows).to_csv(HERE / "candidates.csv", index=False, float_format="%.4f")


def run(trail: float) -> pd.DataFrame:
    """One $1,000 position per pick, bought at the next open; trailing stop
    from the highest close since entry (or entry price); sell at the open if
    it opens below the stop, else at the stop if the day's low touches it."""
    trades = []
    for d, (keep, nxt) in cands.items():
        for t in keep:
            i0 = dates.get_loc(nxt)
            entry = O.at[nxt, t]
            raw_entry = entry / (C.at[nxt, t] / RAW.at[nxt, t])
            hwm, exit_px, exit_day, how = entry, None, None, None
            for i in range(i0, len(dates)):
                day = dates[i]
                stop = hwm * (1 - trail)
                if i > i0 and O.at[day, t] <= stop:
                    exit_px, exit_day, how = O.at[day, t], day, "stop: opened below"
                    break
                if L.at[day, t] <= stop:
                    exit_px, exit_day, how = stop, day, "stop: hit intraday"
                    break
                hwm = max(hwm, C.at[day, t])
            if exit_px is None:
                exit_px, exit_day, how, slip = C.at[last, t], last, "still open (marked at close)", 0.0
            else:
                slip = STOP_SLIP
            adj = C.at[exit_day, t] / RAW.at[exit_day, t]
            ret = exit_px * (1 - COST - slip) / (entry * (1 + COST)) - 1
            trades.append({"drop_day": d.date(), "buy_day": nxt.date(), "ticker": t, "drop": R.at[d, t],
                           "buy_price": round(raw_entry, 2), "sell_day": exit_day.date(), "sell_price": round(exit_px / adj, 2),
                           "exit": how, "days": int(dates.get_loc(exit_day) - i0 + 1), "ret": ret, "pnl_usd": POS * ret})
    return pd.DataFrame(trades)


out = {}
for name, tr in {"3%": 0.03, "8%": 0.08}.items():
    t = run(tr)
    t.to_csv(HERE / f"trades_{name.replace('%', 'pct')}.csv", index=False, float_format="%.4f")
    closed = t[~t["exit"].str.startswith("still")]
    out[name] = {"trades": len(t), "closed": len(closed), "open": int(len(t) - len(closed)),
                 "winners": int((t.ret > 0).sum()), "win_rate": float((t.ret > 0).mean()),
                 "total_pnl_usd": float(t.pnl_usd.sum()), "avg_ret": float(t.ret.mean()),
                 "best": t.loc[t.ret.idxmax(), ["ticker", "ret"]].tolist(), "worst": t.loc[t.ret.idxmin(), ["ticker", "ret"]].tolist(),
                 "capital_used_usd": POS * len(t)}
spy = C["SPY"]
out["spy_same_window"] = float(spy.loc[last] / O.at[dates[dates.get_loc(drop_days[0]) + 1], "SPY"] - 1)
out["window"] = {"first_drop_day": str(drop_days[0].date()), "last_drop_day": str(drop_days[-1].date()), "marked_at": str(last.date())}
(HERE / "summary.json").write_text(json.dumps(out, indent=1, default=str))
print(json.dumps(out, indent=1, default=str))
