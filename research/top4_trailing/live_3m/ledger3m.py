"""Three-month ledger: each day's 4 biggest S&P 500 losers with no obvious
explanation, bought at the next open, exited only by a trailing stop.

Illustration over ~63 trading days, not a pre-registered test.
"Explained" (skipped): earnings the evening before or on the drop day
(Yahoo earnings dates), or a gap down of 8%+ at that morning's open.
Variant "earnings ahead": also skip a stock that reports within the next 10
trading days (checkable before buying). Analyst actions and other news were
not checked.

  python ledger3m.py   -> data.json (for report.html), trades_*.csv, candidates.csv
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

HERE = Path(__file__).resolve().parent
COST, STOP_SLIP, POS = 5 / 1e4, 10 / 1e4, 1000.0
N_DROP_DAYS, AHEAD = 63, 10
TRAILS = {"8%": 0.08, "3%": 0.03}

px = pd.read_parquet(HERE / "prices.parquet")
px["date"] = pd.to_datetime(px["date"])
px = px.sort_values(["ticker", "date"])
f = px["adj_close"] / px["close"]
for c in ("open", "high", "low"):
    px["a" + c] = px[c] * f
px["prev"] = px.groupby("ticker")["adj_close"].shift(1)
px["ret"] = px["adj_close"] / px["prev"] - 1
px["gap"] = px["aopen"] / px["prev"] - 1
W = lambda c: px.pivot(index="date", columns="ticker", values=c)
C, O, L, R, G, V, RAW = W("adj_close"), W("aopen"), W("alow"), W("ret"), W("gap"), W("volume"), W("close")
dates = C.index
last = dates[-1]
drop_days = list(dates[-N_DROP_DAYS - 1:-1])

top10 = {}
for d in drop_days:
    r = R.loc[d].drop("SPY", errors="ignore")
    ok = ((RAW.loc[d] >= 20) & (V.loc[d] >= 1e6) & (r <= -0.02)).reindex(r.index).fillna(False)
    top10[d] = r[ok].sort_values().head(10)

ecache = HERE / "earnings_dates.json"
earn = json.loads(ecache.read_text()) if ecache.exists() else {}
for t in sorted({t for s in top10.values() for t in s.index} - set(earn)):
    try:
        e = yf.Ticker(t).get_earnings_dates(limit=16)
        earn[t] = sorted({str(pd.Timestamp(x).tz_localize(None).date()) for x in e.index}) if e is not None else None
    except Exception:
        earn[t] = None
ecache.write_text(json.dumps(earn, indent=1))
E = {t: [pd.Timestamp(x) for x in v] if v else None for t, v in earn.items()}


def reasons(t, d, ahead: bool):
    i = dates.get_loc(d)
    prev_day, why = dates[i - 1], []
    ed = E.get(t)
    if ed is None:
        why.append("earnings date unknown")
    else:
        if any(x in (prev_day, d) for x in ed):
            why.append("earnings")
        if ahead:
            buy = dates[i + 1]
            horizon = dates[min(i + 1 + AHEAD, len(dates) - 1)] if i + 1 + AHEAD < len(dates) else buy + pd.Timedelta(days=15)
            if any(buy <= x <= horizon for x in ed):
                why.append("earnings within 10 days")
    if G.at[d, t] <= -0.08:
        why.append(f"gapped {G.at[d, t]*100:.1f}% at open")
    return why


def picks(ahead: bool):
    out, cand_rows = {}, []
    for d in drop_days:
        keep = []
        for rank, (t, r) in enumerate(top10[d].items(), 1):
            why = reasons(t, d, ahead)
            chosen = not why and len(keep) < 4
            if chosen:
                keep.append(t)
            cand_rows.append({"drop_day": str(d.date()), "rank": rank, "ticker": t, "drop": float(r), "excluded": "; ".join(why), "picked": chosen})
        out[d] = keep
    return out, cand_rows


def run(sel: dict, trail: float):
    trades = []
    for d, keep in sel.items():
        nxt = dates[dates.get_loc(d) + 1]
        for t in keep:
            i0 = dates.get_loc(nxt)
            entry = O.at[nxt, t]
            if not np.isfinite(entry):
                continue
            hwm, ex, xd, how = entry, None, None, None
            path = []
            for i in range(i0, len(dates)):
                day = dates[i]
                stop = hwm * (1 - trail)
                if i > i0 and np.isfinite(O.at[day, t]) and O.at[day, t] <= stop:
                    ex, xd, how = O.at[day, t], day, "stop: opened below"; break
                if np.isfinite(L.at[day, t]) and L.at[day, t] <= stop:
                    ex, xd, how = stop, day, "stop: hit intraday"; break
                if np.isfinite(C.at[day, t]):
                    hwm = max(hwm, C.at[day, t])
                path.append((str(day.date()), float(C.at[day, t] / entry)))
            slip = STOP_SLIP
            if ex is None:
                ex, xd, how, slip = C.at[last, t], last, "open", 0.0
            ret = ex * (1 - COST - slip) / (entry * (1 + COST)) - 1
            adj_in, adj_out = C.at[nxt, t] / RAW.at[nxt, t], C.at[xd, t] / RAW.at[xd, t]
            ed = E.get(t) or []
            trades.append({"drop_day": str(d.date()), "buy_day": str(nxt.date()), "ticker": t, "drop": float(R.at[d, t]),
                           "buy": round(float(entry / adj_in), 2), "sell_day": str(xd.date()), "sell": round(float(ex / adj_out), 2),
                           "exit": how, "days": int(dates.get_loc(xd) - i0 + 1), "ret": float(ret), "pnl": float(POS * ret),
                           "earnings_in_hold": bool(any(nxt <= x <= xd for x in ed)), "path": path})
    return trades


def daily(trades):
    """Daily marked-to-market P&L with $1,000 per trade, and open positions."""
    rows = []
    for day in dates[dates >= dates[dates.get_loc(drop_days[0]) + 1]]:
        ds = str(day.date())
        realized = sum(t["pnl"] for t in trades if t["exit"] != "open" and t["sell_day"] <= ds)
        unreal, n_open = 0.0, 0
        for t in trades:
            if t["buy_day"] <= ds and (t["exit"] == "open" or t["sell_day"] > ds):
                v = dict(t["path"]).get(ds)
                if v is not None:
                    unreal += POS * (v * (1 - COST) / (1 + COST) - 1); n_open += 1
        rows.append({"date": ds, "pnl": realized + unreal, "realized": realized, "open": n_open})
    return rows


def summary(trades):
    if not trades:
        return {}
    r = np.array([t["ret"] for t in trades]); closed = [t for t in trades if t["exit"] != "open"]
    rc = np.array([t["ret"] for t in closed]) if closed else np.array([0.0])
    return {"trades": len(trades), "open": len(trades) - len(closed), "win_rate": float((r > 0).mean()), "pnl": float(r.sum() * POS),
            "avg": float(r.mean()), "avg_win": float(r[r > 0].mean()) if (r > 0).any() else 0.0, "avg_loss": float(r[r <= 0].mean()) if (r <= 0).any() else 0.0,
            "closed_win_rate": float((rc > 0).mean()), "avg_days_closed": float(np.mean([t["days"] for t in closed])) if closed else 0.0,
            "earnings_in_hold": int(sum(t["earnings_in_hold"] for t in trades)),
            "best": max(trades, key=lambda t: t["ret"])["ticker"], "best_ret": float(r.max()),
            "worst": min(trades, key=lambda t: t["ret"])["ticker"], "worst_ret": float(r.min())}


def max_dd(series):
    peak, dd = 0.0, 0.0
    for v in series:
        peak = max(peak, v); dd = min(dd, v - peak)
    return dd


data = {"window": {"first_drop_day": str(drop_days[0].date()), "last_drop_day": str(drop_days[-1].date()), "marked_at": str(last.date()),
                   "drop_days": len(drop_days)}, "variants": {}, "notes": {"missing_tickers": sorted(set(pd.read_csv(HERE.parent.parent / 'dip_rebound/data/universe.csv').query("index=='SP500'").ticker) - set(C.columns))}}
for ahead in (False, True):
    sel, cand = picks(ahead)
    for tname, trail in TRAILS.items():
        key = f"{tname} | {'skip earnings ahead' if ahead else 'all unexplained'}"
        tr = run(sel, trail)
        dl = daily(tr)
        s = summary(tr)
        s["max_dd_usd"] = max_dd([x["pnl"] for x in dl])
        s["peak_open"] = max(x["open"] for x in dl)
        data["variants"][key] = {"summary": s, "trades": tr, "daily": dl}
        pd.DataFrame([{k: v for k, v in t.items() if k != "path"} for t in tr]).to_csv(HERE / f"trades_{tname.replace('%','pct')}_{'ahead' if ahead else 'all'}.csv", index=False, float_format="%.4f")
    data["candidates_ahead" if ahead else "candidates"] = cand
pd.DataFrame(data["candidates"]).to_csv(HERE / "candidates.csv", index=False, float_format="%.4f")
spy = C["SPY"]
first_buy = dates[dates.get_loc(drop_days[0]) + 1]
data["spy"] = [{"date": str(d.date()), "ret": float(spy.at[d] / O.at[first_buy, "SPY"] - 1)} for d in dates[dates >= first_buy]]
(HERE / "data.json").write_text(json.dumps(data, separators=(",", ":")))
for k, v in data["variants"].items():
    s = v["summary"]
    print(f"{k:<34} trades {s['trades']:3} open {s['open']:2} win {s['win_rate']*100:4.1f}% P&L ${s['pnl']:7.0f} avg {s['avg']*100:+.2f}% "
          f"avg win {s['avg_win']*100:+.1f}% loss {s['avg_loss']*100:+.1f}% maxDD ${s['max_dd_usd']:6.0f} peak open {s['peak_open']} E-in-hold {s['earnings_in_hold']}")
print("SPY over window:", f"{data['spy'][-1]['ret']*100:+.1f}%", "| missing:", data["notes"]["missing_tickers"])
print("unknown earnings:", [t for t, v in earn.items() if v is None])
