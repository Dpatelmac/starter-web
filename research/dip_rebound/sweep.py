"""Drop-threshold sweep: is there ANY drop size or definition with a real edge?

Instead of one 2% cutoff, test four ways of measuring a drop, many cutoffs
each, five holding periods and three volume filters (510 combinations), on
three samples:
  S&P 2005-15   S&P 500/400, 2005-2015
  S&P 2016-26   S&P 500/400, 2016-2026
  New stocks    835 US stocks over $2B not in the S&P 500/400, 2005-2026

Drop measures (all on day t, known at the close):
  fixed      one-day return <= -k%
  vol_adj    one-day return / stock's own daily volatility (prior 60 days) <= -k
  multi3     3-day return <= -k%     multi5   5-day return <= -k%
  vs_sector  one-day return minus sector ETF return <= -k%

Same as backtest.py: volume >= 1M and close >= $20 for every signal, buy at
the next open, edge = signal return minus the same-morning universe average,
t-stat on date-averaged edges. A negative edge means the stock kept falling
relative to other stocks: a short (continuation) signal.

ROBUST, fixed before running: same sign in all three samples, |t| >= 2 in at
least two of them, and |edge| >= 0.10% per trade in every sample (enough to
cover 5 bps per side). With 510 combinations, roughly 25 will show |t| >= 2
in one sample by chance alone; the three-sample rule is what filters those.

Outputs: results/sweep.csv (every combination x sample), results/sweep.json.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import backtest as bt

bt.HOLDS = [1, 2, 3, 5, 10]  # extend forward returns to 10 sessions before prepare()
from holdout import holdout_universe  # noqa: E402

HERE = Path(__file__).resolve().parent
DATA, OUT = HERE / "data", HERE / "results"
HOLDS = bt.HOLDS
MIN_DAYS = 100     # a sample needs signals on at least this many days to count
MIN_EDGE = 0.0010  # 0.10% per trade = 5 bps per side round trip

MEASURES = {
    "fixed": ("One-day drop", "ret", [0.01, 0.015, 0.02, 0.03, 0.04, 0.05, 0.07, 0.10, 0.15], "pct"),
    "vol_adj": ("Drop vs normal daily move", "z", [1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0], "x"),
    "multi3": ("3-day drop", "ret3", [0.02, 0.03, 0.05, 0.07, 0.10, 0.15], "pct"),
    "multi5": ("5-day drop", "ret5", [0.02, 0.03, 0.05, 0.07, 0.10, 0.15], "pct"),
    "vs_sector": ("Drop vs sector ETF", "rel_sector", [0.01, 0.02, 0.03, 0.05, 0.07, 0.10], "pct"),
}
VOLUME = {"1M+ shares": None, "1M+ and 1.5x normal": 1.5, "1M+ and 3x normal": 3.0}


def build(px: pd.DataFrame, etf: pd.DataFrame, uni: pd.DataFrame, use_membership: bool) -> pd.DataFrame:
    px = bt.prepare(px, etf, uni)
    g = px.groupby("ticker", sort=False)
    px["sigma60"] = g["ret"].transform(lambda s: s.shift(1).rolling(60, min_periods=40).std())
    px["z"] = px["ret"] / px["sigma60"]
    px["ret3"] = px["adj_close"] / g["adj_close"].shift(3) - 1
    px["ret5"] = px["adj_close"] / g["adj_close"].shift(5) - 1
    px["rel_sector"] = px["ret"] - px["sector_ret"]
    px = px[(px["date"] >= bt.START) & px["entry"].notna() & px["r1"].notna()]
    elig = (px["volume"] >= bt.MIN_VOL) & (px["close"] >= bt.MIN_PRICE) & px["prev_aclose"].notna()
    if use_membership:
        elig &= px["in_index"]
    base = px.loc[elig, ["date", "ticker", "ret", "z", "ret3", "ret5", "rel_sector", "rvol"]
                  + [f"r{h}" for h in HOLDS]].copy()
    for h in HOLDS:  # edge vs the same-morning universe
        base[f"x{h}"] = base[f"r{h}"] - base.groupby("date")[f"r{h}"].transform("mean")
    return base.reset_index(drop=True)


def clustered(dates: np.ndarray, x: np.ndarray) -> tuple[float, float, int]:
    ok = ~np.isnan(x)
    if ok.sum() == 0:
        return np.nan, np.nan, 0
    s = pd.Series(x[ok]).groupby(dates[ok]).mean()
    n = len(s)
    if n < 2 or s.std(ddof=1) == 0:
        return float(s.mean()), np.nan, n
    return float(s.mean()), float(s.mean() / s.std(ddof=1) * np.sqrt(n)), n


def sweep(samples: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for sname, df in samples.items():
        dates = df["date"].values
        rvol = df["rvol"].values
        xs = {h: df[f"x{h}"].values for h in HOLDS}
        for mkey, (mlabel, col, cuts, unit) in MEASURES.items():
            v = df[col].values
            for k in cuts:
                m_drop = v <= -k
                for vlabel, rv in VOLUME.items():
                    m = m_drop if rv is None else m_drop & (rvol >= rv)
                    if m.sum() == 0:
                        continue
                    d = dates[m]
                    for h in HOLDS:
                        e, t, n = clustered(d, xs[h][m])
                        rows.append({"sample": sname, "measure": mkey, "measure_label": mlabel,
                                     "cutoff": k, "unit": unit, "volume": vlabel, "hold": h,
                                     "signals": int(m.sum()), "days": n, "edge": e, "t": t})
    return pd.DataFrame(rows)


def robust(res: pd.DataFrame) -> pd.DataFrame:
    key = ["measure", "measure_label", "cutoff", "unit", "volume", "hold"]
    w = res.pivot_table(index=key, columns="sample", values=["edge", "t", "days"], aggfunc="first")
    s = list(res["sample"].unique())
    e, t, d = w["edge"][s], w["t"][s], w["days"][s]
    enough = (d >= MIN_DAYS).all(axis=1)
    same = (np.sign(e).nunique(axis=1) == 1) & e.notna().all(axis=1)
    strong = (t.abs() >= 2).sum(axis=1) >= 2
    big = (e.abs() >= MIN_EDGE).all(axis=1)
    out = pd.concat([e.add_prefix("edge: "), t.add_prefix("t: "), d.add_prefix("days: ")], axis=1)
    out["same_sign"], out["t2_in_2plus"], out["edge_ge_cost"], out["enough_days"] = same, strong, big, enough
    out["robust"] = same & strong & big & enough
    out["direction"] = np.where(e.mean(axis=1) > 0, "bounce (buy)", "keeps falling (short)")
    return out.reset_index()


def label(r) -> str:
    k = f"{r['cutoff']*100:g}%" if r["unit"] == "pct" else f"{r['cutoff']:g}x"
    return f"{r['measure_label']} {k}+"


def main() -> None:
    spx, etf, suni = bt.load()
    sp = build(spx, etf, suni, use_membership=True)
    del spx
    huni = holdout_universe()
    hpx = pd.read_parquet(DATA / "holdout_prices.parquet")
    hd = build(hpx, etf, huni[huni["ticker"].isin(hpx["ticker"].unique())], use_membership=False)
    del hpx
    samples = {"S&P 2005-15": sp[sp["date"] <= bt.IS_END], "S&P 2016-26": sp[sp["date"] > bt.IS_END], "New stocks": hd}
    for k, v in samples.items():
        print(f"{k}: {len(v):,} eligible stock-days")

    res = sweep(samples)
    OUT.mkdir(exist_ok=True)
    res.to_csv(OUT / "sweep.csv", index=False, float_format="%.6f")
    rb = robust(res)
    n_combo = len(rb)
    n_t2 = int((res["t"].abs() >= 2).sum())

    pct = lambda v: f"{v*100:+.2f}%" if pd.notna(v) else "   n/a "
    smp = list(samples)
    print(f"\n{n_combo} combinations x {len(smp)} samples = {len(res):,} tests; "
          f"{n_t2} show |t| >= 2 in some sample (about {0.046*len(res):.0f} expected by chance)")

    print("\n3-DAY HOLD, 1M+ SHARES: edge vs same-morning stocks (t-stat)")
    print(f"  {'drop measure':<34}" + "".join(f"{s:>22}" for s in smp) + "   flags")
    base = rb[(rb["hold"] == 3) & (rb["volume"] == "1M+ shares")]
    for _, r in base.iterrows():
        cells = "".join(f"{pct(r[f'edge: {s}'])} ({r[f't: {s}']:5.2f})".rjust(22) if pd.notna(r[f"t: {s}"]) else "n/a".rjust(22) for s in smp)
        flag = "ROBUST " + r["direction"] if r["robust"] else ("same sign" if r["same_sign"] else "")
        print(f"  {label(r):<34}{cells}   {flag}")

    hits = rb[rb["robust"]]
    print(f"\nROBUST across all three samples: {len(hits)} of {n_combo}")
    for _, r in hits.sort_values(["measure", "cutoff", "hold"]).iterrows():
        cells = " | ".join(f"{s} {pct(r[f'edge: {s}'])} t={r[f't: {s}']:.2f}" for s in smp)
        print(f"  {label(r):<30} hold {r['hold']:>2}d  {r['volume']:<20} {r['direction']:<22} {cells}")

    near = rb[~rb["robust"] & rb["same_sign"] & rb["enough_days"] & rb["t2_in_2plus"]]
    print(f"\nNear misses (same sign, |t|>=2 in 2+ samples, but edge under 0.10% somewhere): {len(near)}")
    for _, r in near.sort_values(["measure", "cutoff", "hold"]).head(25).iterrows():
        cells = " | ".join(f"{pct(r[f'edge: {s}'])} t={r[f't: {s}']:.2f}" for s in smp)
        print(f"  {label(r):<30} hold {r['hold']:>2}d  {r['volume']:<20} {r['direction']:<22} {cells}")

    json.dump({"combinations": n_combo, "tests": int(len(res)), "t2_hits": n_t2,
               "robust": hits.to_dict("records"), "near_misses": near.to_dict("records")},
              open(OUT / "sweep.json", "w"), indent=1, default=float)
    rb.to_csv(OUT / "sweep_combined.csv", index=False, float_format="%.6f")


if __name__ == "__main__":
    main()
