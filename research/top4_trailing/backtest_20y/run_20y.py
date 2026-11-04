"""Pre-registered test 10 (see PREREGISTRATION.md): strategy S1 over twenty years.

Run on the Mac from the research folder:

    python3 dip_rebound/fetch_data.py                 # 20-year prices (skip if already done)
    python3 top4_trailing/backtest_20y/run_20y.py     # earnings dates, backtest, report.html

Steps: (1) refresh the T-bill yield, (2) download Yahoo earnings dates for
every S&P 500 member (cached in earnings_dates.json, resumable, ~10 min the
first time), (3) run S1 from 2005, (4) write results.json, trades.csv and
report.html next to this file.

Options: --skip-fetch (use cached earnings dates only), --smoke (quick code
check on 2024-2026 using the 6-year test's cached earnings dates).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent                    # the research/ folder
DATA = ROOT / "dip_rebound" / "data"
COST, STOP_SLIP, POS, ACCOUNT = 5 / 1e4, 10 / 1e4, 1000.0, 24000.0
TRAIL, CAP, SECTOR_MAX, COOL, AHEAD = 0.12, 24, 2, 10, 10
START_DROP, TEST_END = pd.Timestamp("2005-01-03"), pd.Timestamp("2020-10-30")


def log(*a):
    print(*a, flush=True)


# --------------------------------------------------------------------------- data
def refresh_irx():
    import yfinance as yf
    try:
        irx = yf.download("^IRX", start="2003-01-01", progress=False, auto_adjust=False)
        s = (irx["Close"].squeeze() if "Close" in irx else irx.squeeze()).dropna().rename("irx")
        if len(s) > 1000:
            s.to_frame().to_parquet(DATA / "irx.parquet")
            log(f"T-bill yield refreshed through {s.index.max().date()}")
    except Exception as e:
        log("T-bill refresh failed, using committed copy:", e)


def fetch_earnings(tickers, cache: Path):
    import yfinance as yf
    earn = json.loads(cache.read_text()) if cache.exists() else {}
    todo = [t for t in tickers if t not in earn]
    log(f"earnings dates: {len(earn)} cached, {len(todo)} to download")
    for i, t in enumerate(todo):
        for attempt in range(4):
            try:
                e = yf.Ticker(t).get_earnings_dates(limit=100)
                earn[t] = sorted({str(pd.Timestamp(x).tz_localize(None).date()) for x in e.index}) if e is not None and len(e) else None
                break
            except Exception:
                earn[t] = None
                time.sleep(3 * (attempt + 1))
        if i % 25 == 0:
            cache.write_text(json.dumps(earn))
            log(f"  {i + 1}/{len(todo)}")
        time.sleep(0.3)
    cache.write_text(json.dumps(earn))
    return earn


# --------------------------------------------------------------------------- backtest
def run(px, uni, earn, irx, start, end_date=None):
    px = px[px["ticker"].isin(uni.index)].copy()
    px["date"] = pd.to_datetime(px["date"])
    px = px.sort_values(["ticker", "date"])
    f = px["adj_close"] / px["close"]
    px["aopen"], px["alow"] = px["open"] * f, px["low"] * f
    px["prev"] = px.groupby("ticker")["adj_close"].shift(1)
    px["ret"] = px["adj_close"] / px["prev"] - 1
    px["gap"] = px["aopen"] / px["prev"] - 1
    Wd = lambda c: px.pivot(index="date", columns="ticker", values=c)
    C, O, L, R, G, V, RAW = Wd("adj_close"), Wd("aopen"), Wd("alow"), Wd("ret"), Wd("gap"), Wd("volume"), Wd("close")
    if end_date is not None:
        keep = C.index <= end_date
        C, O, L, R, G, V, RAW = [x[keep] for x in (C, O, L, R, G, V, RAW)]
    dates = C.index
    DI = {d: i for i, d in enumerate(dates)}
    COL = {t: j for j, t in enumerate(C.columns)}
    Cv, Ov, Lv, Rv, Gv, Vv, RAWv = C.values, O.values, L.values, R.values, G.values, V.values, RAW.values
    added = pd.to_datetime(uni["sp500_added"]).reindex(C.columns).values
    member = dates.values[:, None] >= added[None, :]
    elig = member & (RAWv >= 20) & (Vv >= 1e6) & (Rv <= -0.02)
    drop_days = [d for d in dates if d >= start and DI[d] < len(dates) - 1]
    SECTOR = uni["sector"].to_dict()
    E = {t: [pd.Timestamp(x) for x in v] for t, v in earn.items() if v}
    FIRST_E = {t: min(v) for t, v in E.items()}
    tick = np.array(C.columns)

    quality = {}          # year -> [checked, unknown-history]

    def explained(t, d):
        i = DI[d]
        y = d.year
        q = quality.setdefault(y, [0, 0])
        q[0] += 1
        ed = E.get(t)
        if not ed or d < FIRST_E[t] - pd.Timedelta(days=100):
            q[1] += 1
            return True
        if any(x in (dates[i - 1], d) for x in ed):
            return True
        buy = dates[i + 1]
        hz = dates[i + 1 + AHEAD] if i + 1 + AHEAD < len(dates) else buy + pd.Timedelta(days=15)
        if any(buy <= x <= hz for x in ed):
            return True
        return Gv[i, COL[t]] <= -0.08

    def path(j, i0):
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

    trades, open_until, last_stop = [], [], {}
    for d in drop_days:
        i = DI[d]
        i0 = i + 1
        open_until = [(x, t) for x, t in open_until if x >= i0]
        held = {t for _, t in open_until}
        idx = np.flatnonzero(elig[i])
        order = idx[np.argsort(Rv[i, idx])]
        n, per_sector = 0, {}
        for j in order:
            if n == 4 or len(open_until) >= CAP:
                break
            t = tick[j]
            if explained(t, d):
                continue
            if t in held or (t in last_stop and i0 - last_stop[t] <= COOL) or per_sector.get(SECTOR.get(t), 0) >= SECTOR_MAX:
                continue
            if not np.isfinite(Ov[i0, j]):
                continue
            entry, xi, xp, how, marks = path(j, i0)
            slip = STOP_SLIP if how.startswith("stop") else 0.0
            ret = xp * (1 - COST - slip) / (entry * (1 + COST)) - 1
            ed = E.get(t, [])
            trades.append({"drop_day": str(d.date()), "buy_day": str(dates[i0].date()), "i0": i0, "xi": xi, "ticker": t,
                           "sector": SECTOR.get(t, ""), "drop": round(float(Rv[i, j]), 4),
                           "buy": round(float(entry * RAWv[i0, j] / Cv[i0, j]), 2), "sell_day": str(dates[xi].date()),
                           "sell": round(float(xp * RAWv[xi, j] / Cv[xi, j]), 2), "exit": how, "days": int(xi - i0 + 1),
                           "ret": round(float(ret), 5), "pnl": round(float(POS * ret), 2),
                           "earnings_in_hold": bool(any(dates[i0] <= x <= dates[xi] for x in ed)), "marks": marks})
            open_until.append((xi if how != "open" else 10**9, t))
            if how.startswith("stop"):
                last_stop[t] = xi
            per_sector[SECTOR.get(t)] = per_sector.get(SECTOR.get(t), 0) + 1
            n += 1

    # Account value with and without T-bill interest on idle cash.
    first = DI[drop_days[0]] + 1
    n = len(dates) - first
    flows, posval, nopen = np.zeros(n), np.zeros(n), np.zeros(n, int)
    for t in trades:
        a, b = t["i0"] - first, t["xi"] - first
        flows[a] -= POS
        closed = t["exit"] != "open"
        if closed:
            flows[b] += POS * (1 + t["ret"])
        end = b if closed else n
        for k, day in enumerate(range(a, end)):
            if k < len(t["marks"]):
                posval[day] += POS * t["marks"][k] * (1 - COST) / (1 + COST)
                nopen[day] += 1
    rf = (irx.reindex(dates[first:]).ffill().bfill() / 100 / 252).values
    out = {}
    for label, r_ in (("with_interest", rf), ("no_interest", np.zeros(n))):
        cash, vals = ACCOUNT, np.zeros(n)
        for k in range(n):
            cash = cash * (1 + r_[k]) + flows[k]
            vals[k] = cash + posval[k]
        out[label] = pd.Series(vals, index=dates[first:])
    return {"trades": trades, "value": out, "open": pd.Series(nopen, index=dates[first:]), "quality": quality,
            "dates": dates, "first_buy": dates[first]}


def stats(v: pd.Series, a, b, irx):
    v = v.loc[a:b]
    if len(v) < 5:
        return None
    base = v.iloc[0]
    r = v.pct_change().dropna()
    rf = (irx.reindex(r.index).ffill().bfill() / 100 / 252)
    yrs = (v.index[-1] - v.index[0]).days / 365.25
    return {"profit": float(v.iloc[-1] - base), "return": float(v.iloc[-1] / base - 1),
            "cagr": float((v.iloc[-1] / base) ** (1 / yrs) - 1) if yrs > 0.5 else float(v.iloc[-1] / base - 1),
            "sharpe": float((r - rf).mean() / r.std() * np.sqrt(252)) if r.std() > 0 else None,
            "max_dd": float((v / v.cummax() - 1).min())}


def trade_stats(trades, a, b):
    t = [x for x in trades if a <= x["buy_day"] <= b]
    if not t:
        return {}
    r = np.array([x["ret"] for x in t])
    pnl = sorted((x["pnl"] for x in t), reverse=True)
    tot = sum(pnl)
    return {"trades": len(t), "win_rate": float((r > 0).mean()), "avg_win": float(r[r > 0].mean()) if (r > 0).any() else 0.0,
            "avg_loss": float(r[r <= 0].mean()) if (r <= 0).any() else 0.0, "avg_days": float(np.mean([x["days"] for x in t])),
            "top10_share": float(sum(pnl[:10]) / tot) if tot > 0 else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-fetch", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    if not (DATA / "prices.parquet").exists():
        sys.exit("Missing dip_rebound/data/prices.parquet: run  python3 dip_rebound/fetch_data.py  first.")
    uni = pd.read_csv(DATA / "universe.csv")
    uni = uni[uni["index"] == "SP500"].set_index("ticker")
    if a.smoke:
        earn = json.loads((HERE.parent / "backtest_6y" / "earnings_dates.json").read_text())
        start = pd.Timestamp("2024-01-02")
    else:
        if not a.skip_fetch:
            refresh_irx()
        cache = HERE / "earnings_dates.json"
        earn = json.loads(cache.read_text()) if a.skip_fetch and cache.exists() else fetch_earnings(list(uni.index), cache)
        start = START_DROP
    irx = pd.read_parquet(DATA / "irx.parquet")["irx"]
    irx.index = pd.to_datetime(irx.index)
    log("loading prices ...")
    px = pd.read_parquet(DATA / "prices.parquet")
    etf = pd.read_parquet(DATA / "etf.parquet")
    log("running S1 ...")
    res = run(px, uni, earn, irx, start)
    dates, fb = res["dates"], res["first_buy"]
    spy_px = etf[etf.ticker == "SPY"].assign(date=lambda d: pd.to_datetime(d["date"])).set_index("date")
    spy_open = spy_px["open"] * spy_px["adj_close"] / spy_px["close"]
    spy = ACCOUNT * spy_px["adj_close"].loc[fb:] / spy_open.loc[fb]
    last = str(dates[-1].date())
    test_end = str(TEST_END.date()) if not a.smoke else last
    periods = {"Never tested: 2005 - Oct 2020": (str(fb.date()), test_end),
               "2010 - Oct 2020 (robustness)": ("2010-01-01", test_end),
               "Full period": (str(fb.date()), last),
               "2005-2009": (str(fb.date()), "2009-12-31"), "2010-2014": ("2010-01-01", "2014-12-31"),
               "2015-2019": ("2015-01-01", "2019-12-31"), "2020-2026": ("2020-01-01", last)}
    years = {str(y): (f"{y}-01-01" if y > fb.year else str(fb.date()), f"{y}-12-31") for y in range(fb.year, dates[-1].year + 1)}
    out = {"periods": {}, "years": {}, "meta": {"first_buy": str(fb.date()), "last": last, "smoke": a.smoke,
                                                "tickers_with_earnings": sum(1 for v in earn.values() if v),
                                                "universe": int(len(uni))}}
    V, Vn = res["value"]["with_interest"], res["value"]["no_interest"]
    for p, (s, e) in {**periods, **years}.items():
        blk = {"S1": stats(V, s, e, irx), "S1_no_interest": stats(Vn, s, e, irx), "SPY": stats(spy, s, e, irx),
               "trades": trade_stats(res["trades"], s, e)}
        (out["periods"] if p in periods else out["years"])[p] = blk
    q = {str(y): {"checked": c, "unknown": u, "share": u / c if c else 0.0, "unreliable": bool(c and u / c > 0.30)} for y, (c, u) in sorted(res["quality"].items())}
    out["quality"] = q
    tp = out["periods"]["Never tested: 2005 - Oct 2020"]
    crit = {"profit_beats_spy": tp["S1"]["profit"] > tp["SPY"]["profit"], "sharpe_beats_spy": tp["S1"]["sharpe"] > tp["SPY"]["sharpe"],
            "dd_smaller_than_spy": tp["S1"]["max_dd"] > tp["SPY"]["max_dd"]}
    out["criteria"] = {k: bool(v) for k, v in crit.items()}
    out["pass"] = all(crit.values())
    rb = out["periods"]["2010 - Oct 2020 (robustness)"]
    out["criteria_2010"] = {"profit_beats_spy": bool(rb["S1"]["profit"] > rb["SPY"]["profit"]), "sharpe_beats_spy": bool(rb["S1"]["sharpe"] > rb["SPY"]["sharpe"]),
                            "dd_smaller_than_spy": bool(rb["S1"]["max_dd"] > rb["SPY"]["max_dd"])}
    tr = res["trades"]
    out["top_trades"] = [{k: x[k] for k in ("ticker", "buy_day", "sell_day", "ret", "pnl")} for x in sorted(tr, key=lambda x: -x["pnl"])[:10]]
    out["worst_trades"] = [{k: x[k] for k in ("ticker", "buy_day", "sell_day", "ret", "pnl")} for x in sorted(tr, key=lambda x: x["pnl"])[:10]]
    sec = pd.Series([x["sector"] for x in tr]).value_counts()
    out["sectors"] = (sec / sec.sum()).round(3).to_dict()
    wk = lambda s: [[str(d.date()), round(float(x), 2)] for d, x in s.resample("W-FRI").last().dropna().items()]
    out["curves"] = {"S1": wk(V), "S1_no_interest": wk(Vn), "SPY": wk(spy)}
    out["trades"] = tr
    out["dates"] = [str(d.date()) for d in dates]
    name = "results_smoke.json" if a.smoke else "results.json"
    (HERE / name).write_text(json.dumps(out, separators=(",", ":"), default=lambda o: None))
    pd.DataFrame([{k: v for k, v in x.items() if k not in ("marks", "i0", "xi")} for x in tr]).to_csv(
        HERE / ("trades_smoke.csv" if a.smoke else "trades.csv"), index=False)

    for p, blk in out["periods"].items():
        s, n_, y = blk["S1"], blk["S1_no_interest"], blk["SPY"]
        if not s:
            continue
        log(f"{p:<32} S1 ${s['profit']:>9,.0f} ({s['cagr']*100:5.1f}%/yr) Sharpe {s['sharpe']:.2f} DD {s['max_dd']*100:6.1f}% | "
            f"no-interest ${n_['profit']:>9,.0f} | SPY ${y['profit']:>9,.0f} ({y['cagr']*100:5.1f}%/yr) Sharpe {y['sharpe']:.2f} DD {y['max_dd']*100:6.1f}%")
    log("criteria (never-tested period):", out["criteria"], "->", "PASS" if out["pass"] else "FAIL")
    log("unreliable years (earnings history):", [y for y, v in q.items() if v["unreliable"]])
    from build_report import build
    path = build(out, HERE / ("report_smoke.html" if a.smoke else "report.html"))
    log("report:", path)


if __name__ == "__main__":
    sys.path.insert(0, str(HERE))
    main()
