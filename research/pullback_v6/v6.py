"""Pre-registered test 7 (see PREREGISTRATION.md): the user's pullback
framework, with ignore rules I1-I4 and bounce signals S1-S7.

  python v6.py   -> results/v6.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DIP = HERE.parent / "dip_rebound"
sys.path.insert(0, str(DIP))
import backtest as bt  # noqa: E402
from holdout import holdout_universe  # noqa: E402

OUT = HERE / "results"
SAMPLES = {"S&P 2005-15": ("sp", "2005-01-01", "2015-12-31"),
           "S&P 2016-26": ("sp", "2016-01-01", "2026-12-31"),
           "New stocks 2005-26": ("new", "2005-01-01", "2026-12-31")}
HOLD_MAIN = 3


def features(px: pd.DataFrame, etf: pd.DataFrame, uni: pd.DataFrame, member: bool):
    p = bt.prepare(px, etf, uni)
    g = p.groupby("ticker", sort=False)
    # RSI(2), Wilder smoothing
    d = g["adj_close"].diff()
    up, dn = d.clip(lower=0), (-d).clip(lower=0)
    au = up.groupby(p["ticker"]).transform(lambda s: s.ewm(alpha=0.5, adjust=False).mean())
    ad = dn.groupby(p["ticker"]).transform(lambda s: s.ewm(alpha=0.5, adjust=False).mean())
    p["rsi2"] = 100 - 100 / (1 + au / ad.replace(0, np.nan))
    p.loc[ad == 0, "rsi2"] = 100.0
    # ATR(14) and 10-day high
    tr = pd.concat([p["ahigh"] - p["alow"], (p["ahigh"] - p["prev_aclose"]).abs(), (p["alow"] - p["prev_aclose"]).abs()], axis=1).max(axis=1)
    p["atr14"] = tr.groupby(p["ticker"]).transform(lambda s: s.ewm(alpha=1 / 14, adjust=False).mean())
    p["hh10"] = g["ahigh"].transform(lambda s: s.rolling(10, min_periods=10).max())
    # Beta to SPY over the prior 60 days
    x, y = p["ret"], p["spy_ret"]
    roll = lambda s: s.groupby(p["ticker"]).transform(lambda q: q.shift(1).rolling(60, min_periods=40).mean())
    ex, ey, exy, eyy = roll(x), roll(y), roll(x * y), roll(y * y)
    p["beta60"] = (exy - ex * ey) / (eyy - ey * ey)
    # Sector ETF down 3 days in a row (SPY where no sector ETF exists yet)
    e = etf.sort_values(["ticker", "date"]).copy()
    e["r"] = e.groupby("ticker")["adj_close"].pct_change()
    e["down3"] = (e["r"] < 0) & (e.groupby("ticker")["r"].shift(1) < 0) & (e.groupby("ticker")["r"].shift(2) < 0)
    d3 = e.pivot(index="date", columns="ticker", values="down3")
    look = d3.stack().rename("sec_down3").reset_index().rename(columns={"ticker": "sector_etf"})
    p = p.merge(look, on=["date", "sector_etf"], how="left")
    spy3 = d3["SPY"].rename("spy_down3").reset_index()
    p = p.merge(spy3, on="date", how="left")
    p["sec_down3"] = p["sec_down3"].astype("boolean").fillna(p["spy_down3"].astype("boolean")).fillna(False).astype(bool)

    p = p[(p["date"] >= bt.START) & p["entry"].notna() & p["r1"].notna()]
    elig = (p["volume"] >= bt.MIN_VOL) & (p["close"] >= bt.MIN_PRICE) & p["prev_aclose"].notna()
    if member:
        elig &= p["in_index"]
    base = p[elig].copy()
    for h in bt.HOLDS:
        base[f"x{h}"] = base[f"r{h}"] - base.groupby("date")[f"r{h}"].transform("mean")
    ev = base[base["ret"] <= bt.DROP].copy()
    ev["I1"] = ev["gap"] <= -0.08
    ev["I2"] = ev["close_loc"] >= 0.5
    ev["I3"] = ev["next_gap"] >= 0.015
    ev["I4"] = ev["sec_down3"]
    ev["S1"] = ev["gap"] > -0.01
    ev["S2"] = ev["close_loc"] <= 0.25
    ev["S3"] = (ev["rsi2"] < 5) | (ev["adj_close"] <= ev["hh10"] - 3 * ev["atr14"])
    ev["S4"] = ev["rvol"] >= 3
    ev["S5"] = ev["spy_ret"] <= -0.01
    ev["S6"] = (ev["ret"] - ev["beta60"] * ev["spy_ret"]) > -0.03
    ev["S7"] = ev["next_gap"] <= -0.03
    for c in ["I1", "I2", "I3", "I4", "S1", "S2", "S3", "S4", "S5", "S6", "S7"]:
        ev[c] = ev[c].fillna(False).astype(bool)
    ev["ignore"] = ev[["I1", "I2", "I3", "I4"]].any(axis=1)
    ev["score"] = ev[["S1", "S2", "S3", "S4", "S5", "S6", "S7"]].sum(axis=1)
    return p, ev


RULES = {
    "R_A: ignore list + score >= 3": lambda e: ~e["ignore"] & (e["score"] >= 3),
    "R_B: ignore list + final flush": lambda e: ~e["ignore"] & e["S7"],
    "R_C: ignore list + score >= 3 + final flush": lambda e: ~e["ignore"] & (e["score"] >= 3) & e["S7"],
    "Baseline: every 2% drop": lambda e: pd.Series(True, index=e.index),
}


def edge_stats(sub: pd.DataFrame, h: int) -> dict:
    e, t = bt.clustered(sub, f"x{h}")
    return {"signals": int(len(sub)), "days": int(sub["date"].nunique()), "edge": e, "t": t,
            "raw": float(sub[f"r{h}"].mean()) if len(sub) else float("nan"),
            "win": float(((sub[f"r{h}"] - 2 * bt.COST_BPS_SIDE / 1e4) > 0).mean()) if len(sub) else float("nan")}


def perf(eq: pd.Series, a: str, b: str, rf: pd.Series) -> dict:
    w = eq.loc[a:b]
    w = w / w.iloc[0]
    r = w.pct_change().dropna()
    x = r - rf.reindex(r.index).fillna(0)
    yrs = (w.index[-1] - w.index[0]).days / 365.25
    m = w.resample("ME").last().pct_change().dropna()
    return {"cagr": float(w.iloc[-1] ** (1 / yrs) - 1), "sharpe": float(x.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else float("nan"),
            "max_dd": float((w / w.cummax() - 1).min()), "month_win": float((m > 0).mean()), "vol": float(r.std() * np.sqrt(252))}


def main() -> None:
    etf = pd.read_parquet(DIP / "data" / "etf.parquet")
    irx = pd.read_parquet(DIP / "data" / "irx.parquet")["irx"]
    irx.index = pd.to_datetime(irx.index)
    rf = irx / 100 / 252
    spx, _, suni = bt.load()
    hpx = pd.read_parquet(DIP / "data" / "holdout_prices.parquet")
    huni = holdout_universe()
    U = {"sp": features(spx, etf, suni, True), "new": features(hpx, etf, huni[huni.ticker.isin(hpx.ticker.unique())], False)}
    del spx, hpx
    spy = etf[etf.ticker == "SPY"].set_index("date")["adj_close"]

    res = {"rules": {}, "marginal": {}, "by_score": {}, "spy": {}}
    for sname, (u, a, b) in SAMPLES.items():
        res["spy"][sname] = perf(spy, a, b, rf)
    for rname, f in RULES.items():
        res["rules"][rname] = {}
        for u, (p, ev) in U.items():
            sub = ev[f(ev).values]
            dates = pd.DatetimeIndex(sorted(p["date"].unique()))
            curves = {c: bt.simulate(sub, p, dates, HOLD_MAIN, cost_bps=c, min_slots=10) for c in (5, 10, 20)}
            for sname, (uu, a, b) in SAMPLES.items():
                if uu != u:
                    continue
                s = sub[(sub["date"] >= a) & (sub["date"] <= b)]
                blk = {f"hold_{h}d": edge_stats(s, h) for h in bt.HOLDS}
                for c, eq in curves.items():
                    blk[f"port_{c}bps"] = perf(eq, a, b, rf)
                res["rules"][rname][sname] = blk
    # Marginal effect of each rule/signal and edge by score (3-day hold, before the ignore list)
    for u, (p, ev) in U.items():
        for sname, (uu, a, b) in SAMPLES.items():
            if uu != u:
                continue
            s = ev[(ev["date"] >= a) & (ev["date"] <= b)]
            mg = {}
            for c in ["I1", "I2", "I3", "I4", "S1", "S2", "S3", "S4", "S5", "S6", "S7"]:
                mg[c] = {"true": edge_stats(s[s[c]], HOLD_MAIN), "false": edge_stats(s[~s[c]], HOLD_MAIN)}
            res["marginal"][sname] = mg
            kept = s[~s["ignore"]]
            res["by_score"][sname] = {int(k): edge_stats(g, HOLD_MAIN) for k, g in kept.groupby("score") if len(g) >= 100}
    crit = {}
    for rname in list(RULES)[:3]:
        c = {}
        for sname in SAMPLES:
            r = res["rules"][rname][sname]
            e3, pt = r[f"hold_{HOLD_MAIN}d"], r["port_5bps"]
            c[sname] = {"edge_ge_cost_t2": bool(e3["edge"] >= 0.001 and e3["t"] >= 2),
                        "sharpe_beats_spy": bool(pt["sharpe"] > res["spy"][sname]["sharpe"]),
                        "dd_smaller_than_spy": bool(pt["max_dd"] > res["spy"][sname]["max_dd"])}
        crit[rname] = {"by_sample": c, "pass": all(all(v.values()) for v in c.values())}
    res["criteria"] = crit
    OUT.mkdir(exist_ok=True)
    (OUT / "v6.json").write_text(json.dumps(res, indent=1, default=float))

    pc = lambda v, d=2: f"{v*100:+.{d}f}%" if v == v else "  n/a"
    for rname in RULES:
        print(f"\n{rname}")
        for sname in SAMPLES:
            r = res["rules"][rname][sname]; e = r["hold_3d"]; q, q20 = r["port_5bps"], r["port_20bps"]
            print(f"  {sname:<20} n={e['signals']:>6,} edge {pc(e['edge'])} t={e['t']:5.2f} raw {pc(e['raw'])} win {e['win']*100:4.1f}% | "
                  f"port CAGR {q['cagr']*100:5.1f}% Sharpe {q['sharpe']:.2f} maxDD {q['max_dd']*100:4.0f}% months+ {q['month_win']*100:3.0f}% | 20bps CAGR {q20['cagr']*100:5.1f}%")
        print("   1/2/5d edge:", " | ".join(f"{s}: " + " ".join(pc(res['rules'][rname][s][f'hold_{h}d']['edge']) for h in (1, 2, 5)) for s in SAMPLES))
    print("\nSPY:", {s: (round(v['cagr'], 3), round(v['sharpe'], 2), round(v['max_dd'], 2)) for s, v in res["spy"].items()})
    print("\nMarginal (3d edge when TRUE vs FALSE, t):")
    for c in ["I1", "I2", "I3", "I4", "S1", "S2", "S3", "S4", "S5", "S6", "S7"]:
        print(f"  {c}: " + " | ".join(f"{s[:11]} T {pc(res['marginal'][s][c]['true']['edge'])} (t {res['marginal'][s][c]['true']['t']:.1f}, n {res['marginal'][s][c]['true']['signals']}) F {pc(res['marginal'][s][c]['false']['edge'])}" for s in SAMPLES))
    print("\nEdge by score (after ignore list):")
    for s in SAMPLES:
        print(f"  {s}: " + "  ".join(f"{k}: {pc(v['edge'])} (t {v['t']:.1f}, n {v['signals']})" for k, v in res["by_score"][s].items()))
    print("\nCRITERIA:")
    for k, v in crit.items():
        print(f"  {k}: pass={v['pass']}  {v['by_sample']}")


if __name__ == "__main__":
    main()
