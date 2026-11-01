"""Pre-registered test 4 (see PREREGISTRATION.md): cash-secured put-write
layer, judged on the CBOE S&P 500 PutWrite index (^PUT), with assumed costs
and US taxes, in two periods (before / after the index was launched).

  python putwrite.py   -> results/putwrite.json
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

HERE = Path(__file__).resolve().parent
OUT = HERE / "results"
PERIODS = {"1996-07 to 2007-06 (before launch)": ("1996-08-02", "2007-06-30"),
           "2007-07 to 2026-10 (after launch)": ("2007-07-01", "2026-10-30")}
CONTEXT = {"2020-01 to 2026-10 (crowded era)": ("2020-01-01", "2026-10-30")}
COST = {"base": 0.005, "stress": 0.010}          # ASSUMPTION: yearly drag
TAX = {"ord": 0.32, "qdiv": 0.15, "ltcg": 0.15, "s1256": 0.6 * 0.15 + 0.4 * 0.32}  # ASSUMPTION


def load() -> pd.DataFrame:
    def get(t, col="Close"):
        d = yf.download(t, start="1989-01-01", progress=False, auto_adjust=False)
        return d[col].squeeze().rename(t)
    df = pd.concat([get("^PUT"), get("SPY", "Adj Close").rename("SPY_TR"), get("SPY").rename("SPY_PX"),
                    get("^IRX"), get("^VIX"), get("^GSPC"), get("XYLD", "Adj Close").rename("XYLD_TR")], axis=1)
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df.sort_index()


def third_fridays(idx: pd.DatetimeIndex) -> set:
    """Roll dates: last trading day on or before each month's third Friday."""
    out = set()
    for (y, m), _ in pd.Series(idx, index=idx).groupby([idx.year, idx.month]):
        first = pd.Timestamp(y, m, 1)
        tf = first + pd.offsets.Week(weekday=4) * (3 if first.weekday() != 4 else 2)
        if first.weekday() == 4:
            tf = first + pd.Timedelta(days=14)
        cand = idx[(idx <= tf) & (idx.year == y) & (idx.month == m)]
        if len(cand):
            out.add(cand[-1])
    return out


def components(df: pd.DataFrame, name: str, cost: float) -> pd.DataFrame:
    """Daily return split into tax buckets for each strategy."""
    rf = df["rf"]
    c = pd.DataFrame(0.0, index=df.index, columns=["ord", "qdiv", "ltcg", "s1256", "unreal"])
    if name == "Put-write layer":
        c["ord"] = rf
        c["s1256"] = df["r_put"] - rf - cost / 252
    elif name == "Put-write + 200-day filter":
        on = df["pw_on"]
        c["ord"] = rf
        c["s1256"] = np.where(on, df["r_put"] - rf - cost / 252, 0.0)
    elif name == "T-bills":
        c["ord"] = rf
    elif name == "SPY buy & hold":
        c["qdiv"] = df["r_spy_tr"] - df["r_spy_px"]
        c["unreal"] = df["r_spy_px"]
    elif name == "50/50 SPY / T-bills":
        c["ord"] = 0.5 * rf
        c["qdiv"] = 0.5 * (df["r_spy_tr"] - df["r_spy_px"])
        c["ltcg"] = 0.5 * df["r_spy_px"]  # ASSUMPTION: rebalancing realizes gains yearly at 15%
    elif name == "XYLD (buy-write fund)":
        c["ord"] = df["r_xyld"]            # ASSUMPTION: distributions taxed as ordinary income
    return c


def run(c: pd.DataFrame, a: str, b: str, taxed: bool) -> pd.Series:
    """Value path from 1.0 over [a, b]; taxes paid each year-end; unrealized SPY gains taxed at the end."""
    c = c.loc[a:b].fillna(0.0)
    V, basis_gain = 1.0, 0.0
    carry = {"ltcg": 0.0, "s1256": 0.0}
    acc = {k: 0.0 for k in ["ord", "qdiv", "ltcg", "s1256"]}
    vals = []
    years = c.index.year
    for i, (d, row) in enumerate(c.iterrows()):
        r = row.sum()
        if not np.isfinite(r):
            vals.append(V); continue
        for k in acc:
            acc[k] += V * row[k]
        basis_gain += V * row["unreal"]
        V *= 1 + r
        last_of_year = i == len(c) - 1 or years[i + 1] != years[i]
        if taxed and last_of_year:
            tax = TAX["ord"] * max(acc["ord"], 0) + TAX["qdiv"] * max(acc["qdiv"], 0)
            for k in ("ltcg", "s1256"):
                net = acc[k] - carry[k]
                if net > 0:
                    tax += TAX[k] * net; carry[k] = 0.0
                else:
                    carry[k] = -net
            V -= tax
            acc = {k: 0.0 for k in acc}
        vals.append(V)
    s = pd.Series(vals, index=c.index)
    s.attrs["liquidation_tax"] = TAX["ltcg"] * max(basis_gain, 0) if taxed else 0.0
    return s


def metrics(v: pd.Series, rf_v: pd.Series) -> dict:
    m = v.resample("ME").last()
    rm = m.pct_change().dropna()
    rfm = rf_v.resample("ME").last().pct_change().reindex(rm.index).fillna(0)
    yrs = (v.index[-1] - v.index[0]).days / 365.25
    end = v.iloc[-1] - v.attrs.get("liquidation_tax", 0.0)
    dd = (m / m.cummax() - 1).min()
    ddd = (v / v.cummax() - 1).min()
    return {"cagr": float(end ** (1 / yrs) - 1), "vol": float(rm.std() * np.sqrt(12)),
            "sharpe": float((rm - rfm).mean() / rm.std() * np.sqrt(12)),
            "max_dd_monthly": float(dd), "max_dd_daily": float(ddd), "worst_month": float(rm.min())}


def main() -> None:
    df = load()
    df = df[df["^PUT"].notna() | (df.index >= "1996-08-01")]
    df["rf"] = (df["^IRX"].ffill() / 100 / 252).fillna(0)
    df["r_put"] = df["^PUT"].pct_change()
    df["r_spy_tr"] = df["SPY_TR"].pct_change()
    df["r_spy_px"] = df["SPY_PX"].pct_change()
    df["r_xyld"] = df["XYLD_TR"].pct_change()
    sma = df["SPY_TR"].rolling(200).mean()
    rolls = third_fridays(df.index)
    on, state = [], True
    for d in df.index:  # decide at each roll close for the next cycle
        on.append(state)
        if d in rolls and np.isfinite(sma.get(d, np.nan)):
            state = bool(df.at[d, "SPY_TR"] > sma[d])
    df["pw_on"] = on
    df = df.loc["1996-08-05":]

    names = ["Put-write layer", "Put-write + 200-day filter", "SPY buy & hold", "50/50 SPY / T-bills", "T-bills"]
    res = {"periods": {}, "context": {}, "assumptions": {"cost_drag": COST, "tax": TAX}}
    for label, (a, b) in {**PERIODS, **CONTEXT}.items():
        blk = {}
        for taxed in (False, True):
            rf_v = run(components(df, "T-bills", 0), a, b, taxed)
            for cname, cost in COST.items():
                for n in names:
                    v = run(components(df, n, cost), a, b, taxed)
                    key = f"{n} | {cname} | {'after tax' if taxed else 'pre-tax'}"
                    if cname == "stress" and not n.startswith("Put"):
                        continue
                    blk[key] = metrics(v, rf_v)
        (res["periods"] if label in PERIODS else res["context"])[label] = blk

    # Calendar-year returns in stress years (pre-tax, base cost).
    yr = {}
    for n in ["Put-write layer", "SPY buy & hold", "50/50 SPY / T-bills"]:
        v = run(components(df, n, COST["base"]), "1996-08-05", "2026-10-30", False)
        y = v.resample("YE").last().pct_change()
        yr[n] = {int(k.year): float(x) for k, x in y.items() if k.year in (2000, 2001, 2002, 2008, 2009, 2018, 2020, 2022, 2025, 2026)}
    res["stress_years"] = yr

    # Criteria (base cost, after tax, both periods).
    crit = {}
    for label in PERIODS:
        blk = res["periods"][label]
        g = lambda n: blk[f"{n} | base | after tax"]
        p, s, mix, tb = g("Put-write layer"), g("SPY buy & hold"), g("50/50 SPY / T-bills"), g("T-bills")
        crit[label] = {"sharpe_beats_spy": p["sharpe"] > s["sharpe"], "sharpe_beats_5050": p["sharpe"] > mix["sharpe"],
                       "dd_smaller_than_spy": p["max_dd_monthly"] > s["max_dd_monthly"], "cagr_above_tbills": p["cagr"] > tb["cagr"]}
    res["criteria"] = crit
    res["pass"] = all(all(c.values()) for c in crit.values())

    # Thesis check: VIX vs the S&P 500's realized volatility over the next 21 trading days.
    g = df["^GSPC"].dropna()
    lr = np.log(g).diff()
    rv_fwd = lr[::-1].rolling(21).std()[::-1].shift(-1) * np.sqrt(252) * 100
    rv_past = lr.rolling(21).std() * np.sqrt(252) * 100
    vix = df["^VIX"].reindex(g.index)
    gap = (vix - rv_fwd).dropna()
    vrp = {}
    for lab, (a, b) in {"1996-2007": ("1996-08-01", "2007-06-30"), "2007-2019": ("2007-07-01", "2019-12-31"),
                        "2020-2026": ("2020-01-01", "2026-10-30")}.items():
        x = gap.loc[a:b]
        vrp[lab] = {"mean_gap_vol_pts": float(x.mean()), "share_vix_above_realized": float((x > 0).mean())}
    vrp["now"] = {"vix": float(vix.iloc[-1]), "realized_21d_past": float(rv_past.iloc[-1])}
    res["vrp"] = vrp

    # Implementation check: XYLD (buy-write fund) vs the put-write index since XYLD's launch.
    a, b = "2013-07-01", "2026-10-30"
    res["xyld_check"] = {n: metrics(run(components(df, n, 0.0 if n.startswith("XYLD") else COST["base"]), a, b, False),
                                    run(components(df, "T-bills", 0), a, b, False))
                         for n in ["XYLD (buy-write fund)", "Put-write layer", "SPY buy & hold"]}
    OUT.mkdir(exist_ok=True)
    (OUT / "putwrite.json").write_text(json.dumps(res, indent=1, default=float))

    pct = lambda x: f"{x*100:6.1f}%"
    for label, blk in {**res["periods"], **res["context"]}.items():
        print(f"\n{label}")
        for k, m in blk.items():
            if "stress" in k and "after" not in k:
                continue
            print(f"  {k:<52} CAGR {pct(m['cagr'])}  vol {pct(m['vol'])}  Sharpe {m['sharpe']:5.2f}  maxDD(m) {pct(m['max_dd_monthly'])}  worst month {pct(m['worst_month'])}")
    print("\nCRITERIA:", json.dumps(crit, indent=1)); print("PASS" if res["pass"] else "FAIL")
    print("\nStress years (pre-tax):"); print(pd.DataFrame(yr).map(lambda x: round(x * 100, 1)).to_string())
    print("\nVRP:", json.dumps(vrp, indent=1))
    print("\nXYLD check 2013-07..2026-10 (pre-tax):")
    for n, m in res["xyld_check"].items():
        print(f"  {n:<24} CAGR {pct(m['cagr'])}  vol {pct(m['vol'])}  Sharpe {m['sharpe']:5.2f}  maxDD(m) {pct(m['max_dd_monthly'])}")


if __name__ == "__main__":
    main()
