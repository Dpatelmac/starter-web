"""One-year ledger: top 4 unexplained S&P 500 losers, trailing-stop exits,
32 versions compared side by side.

Each drop day: S&P 500 losers down 2%+ (close >= $20, volume >= 1M), biggest
first. "Explained" (skipped): earnings the evening before or on the drop day,
or an 8%+ gap down at the open; optionally also stocks reporting in the next
10 trading days. Buy up to 4 at the next open, $1,000 each; exit only by the
trailing stop (sell at the open if it opens below the stop, else at the stop
when the day's low touches it; high-water mark = highest close since entry).

Versions: selection (after / top10) x earnings (same-day / also next 10 days)
x stop (3/5/8/12%) x risk controls (none / cap 24 positions, max 2 new buys
per sector per day, no re-buy within 10 days of a stop-out, no doubling up).

Illustration on one year of data, not a pre-registered test.

  python ledger_1y.py   -> data.json, versions.csv, trades CSVs for the main versions
"""

from __future__ import annotations

import json
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

HERE = Path(__file__).resolve().parent
COST, STOP_SLIP, POS = 5 / 1e4, 10 / 1e4, 1000.0
N_DROP_DAYS, AHEAD = 252, 10
TRAILS = {"3%": 0.03, "5%": 0.05, "8%": 0.08, "12%": 0.12}
CAP, SECTOR_MAX, COOL = 24, 2, 10

px = pd.read_parquet(HERE / "prices.parquet")
px["date"] = pd.to_datetime(px["date"])
px = px.sort_values(["ticker", "date"])
f = px["adj_close"] / px["close"]
for c in ("open", "low"):
    px["a" + c] = px[c] * f
px["prev"] = px.groupby("ticker")["adj_close"].shift(1)
px["ret"] = px["adj_close"] / px["prev"] - 1
px["gap"] = px["aopen"] / px["prev"] - 1
W = lambda c: px.pivot(index="date", columns="ticker", values=c)
C, O, L, R, G, V, RAW = W("adj_close"), W("aopen"), W("alow"), W("ret"), W("gap"), W("volume"), W("close")
dates = C.index
DI = {d: i for i, d in enumerate(dates)}
last = dates[-1]
drop_days = list(dates[-N_DROP_DAYS - 1:-1])
uni = pd.read_csv(HERE.parent.parent / "dip_rebound" / "data" / "universe.csv").set_index("ticker")
SECTOR = uni["sector"].to_dict()

losers = {}
for d in drop_days:
    r = R.loc[d].drop("SPY", errors="ignore")
    ok = ((RAW.loc[d] >= 20) & (V.loc[d] >= 1e6) & (r <= -0.02)).reindex(r.index).fillna(False)
    losers[d] = r[ok].sort_values()

ecache = HERE / "earnings_dates.json"
earn = json.loads(ecache.read_text()) if ecache.exists() else {}
E: dict = {}


def earnings_of(t):
    if t not in E:
        if t not in earn:
            try:
                e = yf.Ticker(t).get_earnings_dates(limit=16)
                earn[t] = sorted({str(pd.Timestamp(x).tz_localize(None).date()) for x in e.index}) if e is not None and len(e) else None
            except Exception:
                earn[t] = None
        E[t] = [pd.Timestamp(x) for x in earn[t]] if earn[t] else None
    return E[t]


def explained(t, d, ahead):
    i = DI[d]
    why = []
    ed = earnings_of(t)
    if ed is None:
        why.append("earnings date unknown")
    else:
        if any(x in (dates[i - 1], d) for x in ed):
            why.append("earnings")
        if ahead:
            buy = dates[i + 1]
            hz = dates[i + 1 + AHEAD] if i + 1 + AHEAD < len(dates) else buy + pd.Timedelta(days=15)
            if any(buy <= x <= hz for x in ed):
                why.append("earnings within 10 days")
    if G.at[d, t] <= -0.08:
        why.append(f"gapped {G.at[d, t]*100:.1f}% at open")
    return why


# Pre-compute explanations for every loser that might be checked (cache across versions).
EXPL = {}
for d in drop_days:
    for t in losers[d].index[:60]:
        for ahead in (False, True):
            EXPL[(d, t, ahead)] = explained(t, d, ahead)
ecache.write_text(json.dumps(earn, indent=1))
print("earnings lookups:", len(earn), "unknown:", sum(v is None for v in earn.values()))

PATH = {}


def path_of(t, i0, trail):
    """Independent trailing-stop path of one position bought at the open of day i0."""
    k = (t, i0, trail)
    if k in PATH:
        return PATH[k]
    entry = O.iat[i0, C.columns.get_loc(t)]
    j = C.columns.get_loc(t)
    hwm, out, marks = entry, None, []
    for i in range(i0, len(dates)):
        o, lo, c = O.iat[i, j], L.iat[i, j], C.iat[i, j]
        stop = hwm * (1 - trail)
        if i > i0 and np.isfinite(o) and o <= stop:
            out = (i, o, "stop: opened below"); break
        if np.isfinite(lo) and lo <= stop:
            out = (i, stop, "stop: hit intraday"); break
        if not np.isfinite(c):          # no more data (delisted / acquired): exit at last close
            pi = i - 1
            out = (pi, C.iat[pi, j], "data ended"); break
        hwm = max(hwm, c)
        marks.append(round(float(c / entry), 4))
    if out is None:
        out = (len(dates) - 1, C.iat[len(dates) - 1, j], "open")
    PATH[k] = (entry, out, marks)
    return PATH[k]


def run(mode, ahead, trail, controls):
    trades, cands = [], []
    open_until = []          # (exit index, ticker)
    last_stop = {}
    for d in drop_days:
        i0 = DI[d] + 1
        open_until = [(x, t) for x, t in open_until if x >= i0]
        held = {t for _, t in open_until}
        pool = losers[d].iloc[:10] if mode == "top10" else losers[d].iloc[:60]
        n, per_sector = 0, {}
        for rank, (t, r) in enumerate(pool.items(), 1):
            if n == 4:
                break
            why = list(EXPL[(d, t, ahead)])
            if not why and controls:
                if len(open_until) >= CAP:
                    why.append("position cap full")
                elif t in held:
                    why.append("already held")
                elif t in last_stop and i0 - last_stop[t] <= COOL:
                    why.append("stopped out in last 10 days")
                elif per_sector.get(SECTOR.get(t), 0) >= SECTOR_MAX:
                    why.append("2 already bought in this sector today")
            pick = not why and np.isfinite(O.iat[i0, C.columns.get_loc(t)])
            cands.append({"drop_day": str(d.date()), "rank": rank, "ticker": t, "drop": round(float(r), 4),
                          "excluded": "; ".join(why), "picked": bool(pick)})
            if not pick:
                continue
            entry, (xi, xp, how), marks = path_of(t, i0, trail)
            slip = 0.0 if how in ("open", "data ended") else STOP_SLIP
            ret = xp * (1 - COST - slip) / (entry * (1 + COST)) - 1
            ed = earnings_of(t) or []
            trades.append({"drop_day": str(d.date()), "buy_day": str(dates[i0].date()), "i0": i0, "ticker": t, "sector": SECTOR.get(t, ""),
                           "drop": round(float(r), 4), "buy": round(float(entry / (C.iat[i0, C.columns.get_loc(t)] / RAW.iat[i0, C.columns.get_loc(t)])), 2),
                           "sell_day": str(dates[xi].date()), "xi": xi,
                           "sell": round(float(xp / (C.iat[xi, C.columns.get_loc(t)] / RAW.iat[xi, C.columns.get_loc(t)])), 2),
                           "exit": how, "days": int(xi - i0 + 1), "ret": round(float(ret), 5), "pnl": round(float(POS * ret), 2),
                           "earnings_in_hold": bool(any(dates[i0] <= x <= dates[xi] for x in ed)), "marks": marks})
            open_until.append((xi if how != "open" else 10**9, t))
            if how.startswith("stop"):
                last_stop[t] = xi
            per_sector[SECTOR.get(t)] = per_sector.get(SECTOR.get(t), 0) + 1
            n += 1
    return trades, cands


def daily(trades):
    first = DI[drop_days[0]] + 1
    n = len(dates) - first
    realized, unreal, nopen = np.zeros(n), np.zeros(n), np.zeros(n, int)
    for t in trades:
        a, b = t["i0"] - first, t["xi"] - first
        closed = t["exit"] != "open"
        if closed:
            realized[b:] += t["pnl"]
            span = range(a, b)
        else:
            span = range(a, n)
        for k, day in enumerate(span):
            if k < len(t["marks"]):
                unreal[day] += POS * (t["marks"][k] * (1 - COST) / (1 + COST) - 1)
                nopen[day] += 1
    pnl = realized + unreal
    return [{"date": str(dates[first + i].date()), "pnl": round(float(pnl[i]), 2), "realized": round(float(realized[i]), 2),
             "open": int(nopen[i])} for i in range(n)]


def metrics(trades, dl):
    r = np.array([t["ret"] for t in trades]) if trades else np.array([0.0])
    closed = [t for t in trades if t["exit"] != "open"]
    pnl = np.array([x["pnl"] for x in dl])
    peak = np.maximum.accumulate(np.maximum(pnl, 0))
    half = len(dl) // 2
    peak_open = max(x["open"] for x in dl)
    m = pd.Series(pnl, index=pd.to_datetime([x["date"] for x in dl])).resample("ME").last()
    mchg = m.diff().fillna(m.iloc[0])
    return {"trades": len(trades), "open": len(trades) - len(closed), "win_rate": float((r > 0).mean()),
            "closed_win_rate": float(np.mean([t["ret"] > 0 for t in closed])) if closed else 0.0,
            "pnl": float(pnl[-1]), "realized": float(dl[-1]["realized"]), "open_pnl": float(pnl[-1] - dl[-1]["realized"]),
            "avg": float(r.mean()), "avg_win": float(r[r > 0].mean()) if (r > 0).any() else 0.0,
            "avg_loss": float(r[r <= 0].mean()) if (r <= 0).any() else 0.0,
            "max_dd_usd": float((pnl - peak).min()), "peak_open": int(peak_open),
            "return_on_peak_capital": float(pnl[-1] / (peak_open * POS)) if peak_open else 0.0,
            "h1_pnl": float(pnl[half - 1]), "h2_pnl": float(pnl[-1] - pnl[half - 1]),
            "months_up": int((mchg > 0).sum()), "months": int(len(mchg)),
            "earnings_in_hold": int(sum(t["earnings_in_hold"] for t in trades)),
            "avg_days": float(np.mean([t["days"] for t in closed])) if closed else 0.0}


data = {"window": {"first_drop_day": str(drop_days[0].date()), "last_drop_day": str(drop_days[-1].date()),
                   "marked_at": str(last.date()), "drop_days": len(drop_days),
                   "half_split": None}, "variants": {}, "candidates": {}, "dates": [str(d.date()) for d in dates]}
rows = []
for mode, ahead, (tn, tr), controls in product(("after", "top10"), (False, True), TRAILS.items(), (False, True)):
    filt = "skip earnings ahead" if ahead else "all unexplained"
    ctl = "controls" if controls else "no controls"
    key = f"{tn} | {filt} | {mode} | {ctl}"
    trades, cands = run(mode, ahead, tr, controls)
    dl = daily(trades)
    m = metrics(trades, dl)
    rows.append({"version": key, "selection": mode, "earnings": filt, "stop": tn, "controls": ctl, **m})
    keep_paths = mode == "after"
    data["variants"][key] = {"summary": m, "daily": dl,
                             "trades": [{k: v for k, v in t.items() if keep_paths or k != "marks"} for t in trades]}
    data["candidates"][f"{filt} | {mode} | {ctl} | {tn}"] = cands if (mode == "after" and tn in ("8%", "12%")) else None
    if tn in ("8%", "12%") and mode == "after":
        pd.DataFrame([{k: v for k, v in t.items() if k not in ("marks", "i0", "xi")} for t in trades]).to_csv(
            HERE / f"trades_{tn.replace('%', 'pct')}_{'ahead' if ahead else 'all'}_{mode}_{'ctl' if controls else 'noctl'}.csv", index=False)
data["window"]["half_split"] = data["variants"][rows[0]["version"]]["daily"][len(data["variants"][rows[0]["version"]]["daily"]) // 2 - 1]["date"]
spy = C["SPY"]
first_buy = dates[DI[drop_days[0]] + 1]
data["spy"] = [{"date": str(d.date()), "ret": round(float(spy.at[d] / O.at[first_buy, "SPY"] - 1), 5)} for d in dates[dates >= first_buy]]
vt = pd.DataFrame(rows)
vt.to_csv(HERE / "versions.csv", index=False, float_format="%.4f")
(HERE / "data.json").write_text(json.dumps(data, separators=(",", ":")))
pd.set_option("display.width", 250)
show = vt[["version", "trades", "win_rate", "pnl", "realized", "open_pnl", "max_dd_usd", "peak_open", "return_on_peak_capital", "h1_pnl", "h2_pnl", "months_up", "months"]].copy()
for c in ("win_rate", "return_on_peak_capital"):
    show[c] = (show[c] * 100).round(1)
for c in ("pnl", "realized", "open_pnl", "max_dd_usd", "h1_pnl", "h2_pnl"):
    show[c] = show[c].round(0)
print(show.sort_values("pnl", ascending=False).to_string(index=False))
print("SPY over window:", f"{data['spy'][-1]['ret']*100:+.1f}%", "| half split after", data["window"]["half_split"])
print("data.json KB:", round((HERE / 'data.json').stat().st_size / 1024))
