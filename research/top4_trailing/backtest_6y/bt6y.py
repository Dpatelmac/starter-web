"""Pre-registered test 9 (see PREREGISTRATION.md): the three best one-year
versions of the top-4 unexplained losers strategy, run over six years.

  python fetch6y.py   # prices + earnings dates (cached)
  python bt6y.py      -> results.json, trades_S*.csv
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
COST, STOP_SLIP, POS, ACCOUNT = 5 / 1e4, 10 / 1e4, 1000.0, 24000.0
TRAIL, CAP, SECTOR_MAX, COOL, AHEAD = 0.12, 24, 2, 10, 10
START_DROP, UNSEEN_END = pd.Timestamp("2020-11-02"), pd.Timestamp("2025-10-31")
STRATS = {"S1": ("after", True), "S2": ("after", False), "S3": ("top10", False)}
NAMES = {"S1": "Top 4 after removing explained + skip upcoming earnings",
         "S2": "Top 4 after removing explained",
         "S3": "First 10 losers, then remove explained"}

px = pd.read_parquet(HERE / "prices.parquet")
px["date"] = pd.to_datetime(px["date"])
px = px.sort_values(["ticker", "date"])
f = px["adj_close"] / px["close"]
px["aopen"], px["alow"] = px["open"] * f, px["low"] * f
px["prev"] = px.groupby("ticker")["adj_close"].shift(1)
px["ret"] = px["adj_close"] / px["prev"] - 1
px["gap"] = px["aopen"] / px["prev"] - 1
W = lambda c: px.pivot(index="date", columns="ticker", values=c)
C, O, L, R, G, V, RAW = W("adj_close"), W("aopen"), W("alow"), W("ret"), W("gap"), W("volume"), W("close")
dates = C.index
DI = {d: i for i, d in enumerate(dates)}
COL = {t: j for j, t in enumerate(C.columns)}
Cv, Ov, Lv, RAWv = C.values, O.values, L.values, RAW.values
drop_days = [d for d in dates if d >= START_DROP and DI[d] < len(dates) - 1]

uni = pd.read_csv(ROOT / "dip_rebound/data/universe.csv")
uni = uni[uni["index"] == "SP500"].set_index("ticker")
ADDED = pd.to_datetime(uni["sp500_added"]).to_dict()
SECTOR = uni["sector"].to_dict()
earn = json.loads((HERE / "earnings_dates.json").read_text())
E = {t: [pd.Timestamp(x) for x in v] for t, v in earn.items() if v}
FIRST_E = {t: min(v) for t, v in E.items()}

losers = {}
for d in drop_days:
    r = R.loc[d].drop("SPY", errors="ignore")
    member = pd.Series({t: (t in ADDED and pd.notna(ADDED[t]) and d >= ADDED[t]) for t in r.index})
    ok = ((RAW.loc[d] >= 20) & (V.loc[d] >= 1e6) & (r <= -0.02)).reindex(r.index).fillna(False) & member.reindex(r.index).fillna(False)
    losers[d] = r[ok].sort_values()

EX = {}


def explained(t, d, ahead):
    k = (t, d, ahead)
    if k in EX:
        return EX[k]
    i = DI[d]
    why = []
    ed = E.get(t)
    if not ed or d < FIRST_E[t] - pd.Timedelta(days=100):
        why.append("earnings history unknown")
    else:
        if any(x in (dates[i - 1], d) for x in ed):
            why.append("earnings")
        if ahead:
            buy = dates[i + 1]
            hz = dates[i + 1 + AHEAD] if i + 1 + AHEAD < len(dates) else buy + pd.Timedelta(days=15)
            if any(buy <= x <= hz for x in ed):
                why.append("earnings within 10 days")
    if G.at[d, t] <= -0.08:
        why.append("gapped 8%+ at open")
    EX[k] = why
    return why


def path(t, i0):
    j = COL[t]
    entry = Ov[i0, j]
    hwm, marks = entry, []
    for i in range(i0, len(dates)):
        o, lo, c = Ov[i, j], Lv[i, j], Cv[i, j]
        stop = hwm * (1 - TRAIL)
        if i > i0 and np.isfinite(o) and o <= stop:
            return entry, i, o, "stop: opened below", marks
        if np.isfinite(lo) and lo <= stop:
            return entry, i, stop, "stop: hit intraday", marks
        if not np.isfinite(c):
            return entry, i - 1, Cv[i - 1, j], "data ended", marks
        hwm = max(hwm, c)
        marks.append(round(float(c / entry), 4))
    return entry, len(dates) - 1, Cv[-1, j], "open", marks


def run(mode, ahead):
    trades, skipped_unknown = [], 0
    open_until, last_stop = [], {}
    for d in drop_days:
        i0 = DI[d] + 1
        open_until = [(x, t) for x, t in open_until if x >= i0]
        held = {t for _, t in open_until}
        pool = losers[d].iloc[:10] if mode == "top10" else losers[d]
        n, per_sector = 0, {}
        for t, r in pool.items():
            if n == 4 or len(open_until) >= CAP:
                break
            why = explained(t, d, ahead)
            if why:
                skipped_unknown += "earnings history unknown" in why
                continue
            if t in held or (t in last_stop and i0 - last_stop[t] <= COOL) or per_sector.get(SECTOR.get(t), 0) >= SECTOR_MAX:
                continue
            if not np.isfinite(Ov[i0, COL[t]]):
                continue
            entry, xi, xp, how, marks = path(t, i0)
            slip = STOP_SLIP if how.startswith("stop") else 0.0
            ret = xp * (1 - COST - slip) / (entry * (1 + COST)) - 1
            j = COL[t]
            ed = E.get(t, [])
            trades.append({"drop_day": str(d.date()), "buy_day": str(dates[i0].date()), "i0": i0, "xi": xi, "ticker": t,
                           "sector": SECTOR.get(t, ""), "drop": round(float(r), 4),
                           "buy": round(float(entry * RAWv[i0, j] / Cv[i0, j]), 2), "sell_day": str(dates[xi].date()),
                           "sell": round(float(xp * RAWv[xi, j] / Cv[xi, j]), 2), "exit": how, "days": int(xi - i0 + 1),
                           "ret": round(float(ret), 5), "pnl": round(float(POS * ret), 2),
                           "earnings_in_hold": bool(any(dates[i0] <= x <= dates[xi] for x in ed)), "marks": marks})
            open_until.append((xi if how != "open" else 10**9, t))
            if how.startswith("stop"):
                last_stop[t] = xi
            per_sector[SECTOR.get(t)] = per_sector.get(SECTOR.get(t), 0) + 1
            n += 1
    return trades, skipped_unknown


def account(trades):
    first = DI[drop_days[0]] + 1
    n = len(dates) - first
    realized, unreal, nopen = np.zeros(n), np.zeros(n), np.zeros(n, int)
    for t in trades:
        a, b = t["i0"] - first, t["xi"] - first
        if t["exit"] != "open":
            realized[b:] += t["pnl"]
            span = range(a, b)
        else:
            span = range(a, n)
        for k, day in enumerate(span):
            if k < len(t["marks"]):
                unreal[day] += POS * (t["marks"][k] * (1 - COST) / (1 + COST) - 1)
                nopen[day] += 1
    idx = dates[first:]
    return pd.DataFrame({"value": ACCOUNT + realized + unreal, "realized": realized, "open": nopen}, index=idx)


irx = pd.read_parquet(ROOT / "dip_rebound/data/irx.parquet")["irx"]
irx.index = pd.to_datetime(irx.index)


def stats(value: pd.Series, a, b):
    v = value.loc[a:b]
    base = v.iloc[0] if a != value.index[0] else ACCOUNT
    r = v.pct_change().dropna()
    rf = (irx.reindex(r.index).ffill().fillna(4.0) / 100 / 252)
    yrs = (v.index[-1] - v.index[0]).days / 365.25
    dd = (v / v.cummax() - 1).min()
    return {"profit": float(v.iloc[-1] - base), "return": float(v.iloc[-1] / base - 1),
            "cagr": float((v.iloc[-1] / base) ** (1 / yrs) - 1) if yrs > 0.5 else float(v.iloc[-1] / base - 1),
            "sharpe": float((r - rf).mean() / r.std() * np.sqrt(252)) if r.std() > 0 else float("nan"),
            "max_dd": float(dd), "max_dd_usd": float((v - v.cummax()).min())}


def trade_stats(trades, a, b):
    t = [x for x in trades if a <= x["buy_day"] <= b]
    if not t:
        return {}
    r = np.array([x["ret"] for x in t])
    pnl = sorted((x["pnl"] for x in t), reverse=True)
    tot = sum(pnl)
    return {"trades": len(t), "win_rate": float((r > 0).mean()), "avg_win": float(r[r > 0].mean()) if (r > 0).any() else 0,
            "avg_loss": float(r[r <= 0].mean()) if (r <= 0).any() else 0, "avg_days": float(np.mean([x["days"] for x in t])),
            "top10_share": float(sum(pnl[:10]) / tot) if tot > 0 else float("nan"),
            "earnings_in_hold": int(sum(x["earnings_in_hold"] for x in t))}


spy = C["SPY"]
first_buy = dates[DI[drop_days[0]] + 1]
spy_val = ACCOUNT * spy.loc[first_buy:] / O.at[first_buy, "SPY"]
PERIODS = {"Unseen: Nov 2020 - Oct 2025": (str(first_buy.date()), str(UNSEEN_END.date())),
           "Selection year: Nov 2025 - Nov 2026": ("2025-11-03", str(dates[-1].date())),
           "Full six years": (str(first_buy.date()), str(dates[-1].date()))}
YEARS = {str(y): (f"{y}-01-01" if y > first_buy.year else str(first_buy.date()), f"{y}-12-31") for y in range(first_buy.year, dates[-1].year + 1)}

res = {"strategies": {}, "spy": {}, "names": NAMES, "periods": PERIODS}
for p, (a, b) in {**PERIODS, **YEARS}.items():
    res["spy"][p] = stats(spy_val, a, b)
curves = {"SPY": spy_val}
for k, (mode, ahead) in STRATS.items():
    trades, unk = run(mode, ahead)
    acc = account(trades)
    curves[k] = acc["value"]
    blk = {"skipped_unknown_earnings": unk, "periods": {}, "years": {}}
    for p, (a, b) in PERIODS.items():
        blk["periods"][p] = {**stats(acc["value"], a, b), **trade_stats(trades, a, b), "peak_open": int(acc["open"].loc[a:b].max())}
    for y, (a, b) in YEARS.items():
        blk["years"][y] = {**stats(acc["value"], a, b), **trade_stats(trades, a, b)}
    sec = pd.Series([x["sector"] for x in trades]).value_counts()
    blk["sectors"] = (sec / sec.sum()).round(3).to_dict()
    blk["exits"] = pd.Series([x["exit"] for x in trades]).value_counts().to_dict()
    blk["top_trades"] = [{k2: x[k2] for k2 in ("ticker", "buy_day", "sell_day", "ret", "pnl")} for x in sorted(trades, key=lambda x: -x["pnl"])[:10]]
    blk["worst_trades"] = [{k2: x[k2] for k2 in ("ticker", "buy_day", "sell_day", "ret", "pnl")} for x in sorted(trades, key=lambda x: x["pnl"])[:5]]
    u = blk["periods"]["Unseen: Nov 2020 - Oct 2025"]; s = res["spy"]["Unseen: Nov 2020 - Oct 2025"]
    blk["criteria"] = {"profit_beats_spy": bool(u["profit"] > s["profit"]), "sharpe_beats_spy": bool(u["sharpe"] > s["sharpe"]),
                       "dd_smaller_than_spy": bool(u["max_dd"] > s["max_dd"])}
    blk["pass"] = all(blk["criteria"].values())
    res["strategies"][k] = blk
    res["strategies"][k]["trades"] = trades
    pd.DataFrame([{k2: v for k2, v in x.items() if k2 not in ("marks", "i0", "xi")} for x in trades]).to_csv(HERE / f"trades_{k}.csv", index=False)
    res["strategies"][k]["daily"] = [[str(d.date()), round(float(v), 2), int(o)] for d, v, o in zip(acc.index, acc["value"], acc["open"])]
res["spy_daily"] = [[str(d.date()), round(float(v), 2)] for d, v in spy_val.items()]
res["dates"] = [str(d.date()) for d in dates]
(HERE / "results.json").write_text(json.dumps(res, separators=(",", ":")))

for p in PERIODS:
    s = res["spy"][p]
    print(f"\n{p}\n  {'SPY $24k':<58} profit ${s['profit']:>8,.0f} ({s['return']*100:+5.1f}%, CAGR {s['cagr']*100:4.1f}%) Sharpe {s['sharpe']:.2f} maxDD {s['max_dd']*100:5.1f}%")
    for k in STRATS:
        x = res["strategies"][k]["periods"][p]
        print(f"  {k} {NAMES[k]:<55} profit ${x['profit']:>8,.0f} ({x['return']*100:+5.1f}%, CAGR {x['cagr']*100:4.1f}%) Sharpe {x['sharpe']:.2f} maxDD {x['max_dd']*100:5.1f}% "
              f"| trades {x.get('trades',0)} win {x.get('win_rate',0)*100:.0f}% avg win {x.get('avg_win',0)*100:+.0f}% loss {x.get('avg_loss',0)*100:+.0f}% top10 {x.get('top10_share',0)*100:.0f}%")
print("\nBy year (profit $):")
print("  year   SPY      " + "  ".join(f"{k:>8}" for k in STRATS))
for y in YEARS:
    print(f"  {y}  {res['spy'][y]['profit']:>7,.0f}  " + "  ".join(f"{res['strategies'][k]['years'][y]['profit']:>8,.0f}" for k in STRATS))
for k in STRATS:
    print(k, "criteria", res["strategies"][k]["criteria"], "PASS" if res["strategies"][k]["pass"] else "FAIL", "| skipped (no earnings history):", res["strategies"][k]["skipped_unknown_earnings"])
