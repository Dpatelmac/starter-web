"""Like-for-like comparison of every strategy tested, for the ranking.

Same window (2005-01-03 to 2026-10-30), same cost (5 bps per side; put-write
uses its assumed 0.5%/yr drag), pre-tax, cash earning T-bills where the
strategy holds cash. Metrics from daily values: CAGR, Sharpe (over T-bills),
max drawdown, % of months positive; plus % of trades that made money where a
strategy has discrete trades.

  python compare.py   -> results/compare.json, results/compare.csv
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

R = Path(__file__).resolve().parent.parent
for sub in ("dip_rebound", "momentum_regime", "putwrite"):
    sys.path.insert(0, str(R / sub))
import backtest as bt  # noqa: E402
import weekly as wk  # noqa: E402
import momentum as mo  # noqa: E402
import putwrite as pwm  # noqa: E402
from holdout import holdout_universe  # noqa: E402

A, B = "2005-01-03", "2026-10-30"
OUT = Path(__file__).resolve().parent / "results"
irx = pd.read_parquet(R / "dip_rebound" / "data" / "irx.parquet")["irx"]
irx.index = pd.to_datetime(irx.index)


def metrics(eq: pd.Series) -> dict:
    eq = eq.loc[A:B].dropna()
    eq = eq / eq.iloc[0]
    r = eq.pct_change().dropna()
    rf = (irx.reindex(r.index).ffill().fillna(0) / 100 / 252)
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    m = eq.resample("ME").last().pct_change().dropna()
    return {"cagr": float(eq.iloc[-1] ** (1 / yrs) - 1), "vol": float(r.std() * np.sqrt(252)),
            "sharpe": float((r - rf).mean() / r.std() * np.sqrt(252)),
            "max_dd": float((eq / eq.cummax() - 1).min()), "month_win": float((m > 0).mean()),
            "growth_of_1": float(eq.iloc[-1])}


def main() -> None:
    res = {}
    px, etf, uni = bt.load()
    p = bt.prepare(px, etf, uni)
    g = p.groupby("ticker", sort=False)
    p["ret5"] = p["adj_close"] / g["adj_close"].shift(5) - 1
    p = p[(p["date"] >= bt.START) & p["entry"].notna() & p["r1"].notna()]
    elig = (p["volume"] >= bt.MIN_VOL) & (p["close"] >= bt.MIN_PRICE) & p["prev_aclose"].notna() & p["in_index"]
    base = p[elig]
    dates = pd.DatetimeIndex(sorted(p["date"].unique()))
    cost_c = 2 * bt.COST_BPS_SIDE / 1e4

    dips = base[base["ret"] <= -0.02]
    eq = bt.simulate(dips, p, dates, 3, cost_bps=5)
    res["1. Buy every 2% drop (3-day hold)"] = {**metrics(eq), "trade_win": float(((dips["r3"] - cost_c) > 0).mean())}

    h1 = dips[(dips["ret5_prior"] <= -0.05) & (dips["spy_ret"] <= -0.01)]
    eq = bt.simulate(h1, p, dates, 3, cost_bps=5)
    res["2. Oversold in a selloff (holdout rule, 3-day)"] = {**metrics(eq), "trade_win": float(((h1["r3"] - cost_c) > 0).mean())}

    pb = base[base["ret5"] <= -0.02]
    eq = bt.simulate(pb, p, dates, 5, cost_bps=5)
    res["3. Weekly pullback, daily entries (5-day hold)"] = {**metrics(eq), "trade_win": float(((pb["r5"] - cost_c) > 0).mean())}
    del p, base, dips, h1, pb

    m = wk.Market(px, etf, uni, True)
    eq, _ = wk.simulate(m, 20, None, "none", True, 5)
    res["4. Weekly pullback portfolio (top 20, buffer)"] = {**metrics(eq), "trade_win": None}
    del m

    mm = mo.Market(px, etf, uni, True)
    eq, _, _ = mo.simulate(mm, mo.CFGS[mo.PRIMARY], 5)
    res["5. Regime-gated momentum (full strategy D)"] = {**metrics(eq), "trade_win": None}
    eq, _, _ = mo.simulate(mm, mo.CFGS["A: top-20 momentum, equal weight, always invested"], 5)
    res["5a. Plain top-20 momentum (no risk controls)"] = {**metrics(eq), "trade_win": None}
    eq = mo.spy_regime(mm, 5)
    res["Lead: SPY with 200-day switch (not yet pre-registered)"] = {**metrics(eq), "trade_win": None}
    del mm, px

    df = pwm.load()
    df["rf"] = (df["^IRX"].ffill() / 100 / 252).fillna(0)
    df["r_put"] = df["^PUT"].pct_change()
    df["r_spy_tr"] = df["SPY_TR"].pct_change(); df["r_spy_px"] = df["SPY_PX"].pct_change(); df["r_xyld"] = df["XYLD_TR"].pct_change()
    eq = pwm.run(pwm.components(df, "Put-write layer", pwm.COST["base"]), A, B, False)
    res["6. Put-write layer (CBOE PutWrite index)"] = {**metrics(eq), "trade_win": None}
    eq = pwm.run(pwm.components(df, "50/50 SPY / T-bills", 0), A, B, False)
    res["Benchmark: 50/50 SPY / T-bills"] = {**metrics(eq), "trade_win": None}

    spy = etf[etf.ticker == "SPY"].set_index("date")["adj_close"]
    res["Benchmark: SPY buy & hold"] = {**metrics(spy), "trade_win": None}

    OUT.mkdir(exist_ok=True)
    (OUT / "compare.json").write_text(json.dumps(res, indent=1))
    t = pd.DataFrame(res).T
    t.to_csv(OUT / "compare.csv", float_format="%.4f")
    show = t.copy()
    for c in ("cagr", "vol", "max_dd", "month_win", "trade_win"):
        show[c] = show[c].map(lambda v: "" if v is None or pd.isna(v) else f"{v*100:.1f}%")
    show["sharpe"] = t["sharpe"].map(lambda v: f"{v:.2f}")
    show["growth_of_1"] = t["growth_of_1"].map(lambda v: f"${v:.2f}")
    print(show.sort_values("sharpe", ascending=False).to_string())


if __name__ == "__main__":
    main()
