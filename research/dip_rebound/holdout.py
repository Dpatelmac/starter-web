"""Pre-registered holdout test (see PREREGISTRATION.md).

Runs the fixed H1 rule (dip + stock down 5%+ over the prior 5 sessions + SPY
down 1%+ that day) on US stocks over $2B that are NOT in the S&P 500/400,
using exactly the signal, timing, edge metric and simulator of backtest.py.

  python holdout.py            # downloads holdout prices once, then tests
Outputs: results/holdout.json
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import backtest as bt
from fetch_data import download

HERE = Path(__file__).resolve().parent
DATA, OUT = HERE / "data", HERE / "results"

# Nasdaq screener sectors -> GICS names used by backtest.SECTOR_ETF.
NASDAQ_TO_GICS = {
    "Finance": "Financials", "Consumer Discretionary": "Consumer Discretionary",
    "Technology": "Information Technology", "Health Care": "Health Care",
    "Industrials": "Industrials", "Utilities": "Utilities", "Energy": "Energy",
    "Real Estate": "Real Estate", "Basic Materials": "Materials",
    "Telecommunications": "Communication Services", "Consumer Staples": "Consumer Staples",
}

RULES = {
    "H1: prior 5 days down 5%+ and SPY down 1%+": lambda d: (d["ret5_prior"] <= -0.05) & (d["spy_ret"] <= -0.01),
    "H2: prior 5 days down 5%+": lambda d: d["ret5_prior"] <= -0.05,
    "H3: SPY down 1%+": lambda d: d["spy_ret"] <= -0.01,
    "H0: every dip": lambda d: pd.Series(True, index=d.index),
}


def holdout_universe() -> pd.DataFrame:
    s = pd.read_csv(DATA / "nasdaq_screener_2b.csv")
    s = s[(s["country"] == "United States") & s["symbol"].str.fullmatch(r"[A-Z]{1,5}(\.[A-Z])?")]
    return pd.DataFrame({
        "ticker": s["symbol"].str.replace(".", "-", regex=False),
        "name": s["name"], "sector": s["sector"].map(NASDAQ_TO_GICS),
        "index": "HOLDOUT", "sp500_added": pd.NaT,
    }).drop_duplicates("ticker")


def run_universe(px: pd.DataFrame, etf: pd.DataFrame, uni: pd.DataFrame, use_membership: bool):
    px = bt.prepare(px, etf, uni)
    px = px[(px["date"] >= bt.START) & px["entry"].notna() & px["r1"].notna()]
    elig = (px["volume"] >= bt.MIN_VOL) & (px["close"] >= bt.MIN_PRICE) & px["prev_aclose"].notna()
    if use_membership:
        elig &= px["in_index"]
    base = bt.tagged(px[elig])
    ev = bt.add_edge(base[base["ret"] <= bt.DROP], base)
    return px, base, ev


def score(ev: pd.DataFrame, px: pd.DataFrame, dates: pd.DatetimeIndex) -> dict:
    out = {}
    oos = dates > bt.IS_END
    for name, f in RULES.items():
        sub = ev[f(ev).fillna(False).values]
        e, t = bt.clustered(sub, "x3")
        e_is, t_is = bt.clustered(sub[sub["date"] <= bt.IS_END], "x3")
        e_oos, t_oos = bt.clustered(sub[sub["date"] > bt.IS_END], "x3")
        eq = bt.simulate(sub, px, dates, 3, cost_bps=5)
        eq0 = bt.simulate(sub, px, dates, 3, cost_bps=0)
        out[name] = {
            "signals": int(len(sub)), "days": int(sub["date"].nunique()),
            "edge": e, "t": t, "edge_is": e_is, "t_is": t_is, "edge_oos": e_oos, "t_oos": t_oos,
            "raw3": float(sub["r3"].mean()), "win3": float((sub["r3"] > 0).mean()),
            "port_net": bt.perf(eq), "port_gross": bt.perf(eq0),
            "port_net_2016": bt.perf(eq[oos] / eq[oos].iloc[0]),
            "exposure": float(sub["date"].nunique() / len(dates)),
        }
    return out


def main() -> None:
    uni = holdout_universe()
    path = DATA / "holdout_prices.parquet"
    if not path.exists():
        print(f"downloading {len(uni)} holdout tickers ...")
        download(uni["ticker"].tolist()).to_parquet(path, index=False)
    hpx = pd.read_parquet(path)
    etf = pd.read_parquet(DATA / "etf.parquet")
    uni = uni[uni["ticker"].isin(hpx["ticker"].unique())]
    print(f"holdout: {hpx['ticker'].nunique()} tickers with data, {len(hpx):,} rows")

    hp, hbase, hev = run_universe(hpx, etf, uni, use_membership=False)
    dates = pd.DatetimeIndex(sorted(hp["date"].unique()))
    res = {"universe": "holdout", "tickers": int(hpx["ticker"].nunique()),
           "eligible_stock_days": int(len(hbase)), "rules": score(hev, hp, dates)}

    # Same rules on the original S&P 500/400 universe, for reference.
    spx, setf, suni = bt.load()
    sp, sbase, sev = run_universe(spx, setf, suni, use_membership=True)
    sdates = pd.DatetimeIndex(sorted(sp["date"].unique()))
    res["reference_sp1500ish"] = score(sev, sp, sdates)

    h1 = res["rules"]["H1: prior 5 days down 5%+ and SPY down 1%+"]
    res["verdict"] = {
        "c1_full_edge_t2": bool(h1["edge"] > 0 and h1["t"] >= 2.0),
        "c2_both_halves_positive": bool(h1["edge_is"] > 0 and h1["edge_oos"] > 0),
        "c3_net_cagr_positive": bool(h1["port_net"]["cagr"] > 0),
    }
    res["verdict"]["pass"] = all(res["verdict"].values())
    OUT.mkdir(exist_ok=True)
    (OUT / "holdout.json").write_text(json.dumps(res, indent=1, default=float))

    pct = lambda v: f"{v*100:+.3f}%"
    for label, block in [("HOLDOUT (not in S&P 500/400)", res["rules"]), ("REFERENCE (S&P 500/400)", res["reference_sp1500ish"])]:
        print(f"\n{label}")
        for k, r in block.items():
            p, g = r["port_net"], r["port_gross"]
            print(f"  {k:<44} n={r['signals']:>7,} days={r['days']:>5,} | edge {pct(r['edge'])} t={r['t']:5.2f} | "
                  f"05-15 {pct(r['edge_is'])} t={r['t_is']:5.2f} | 16-26 {pct(r['edge_oos'])} t={r['t_oos']:5.2f} | "
                  f"raw3 {pct(r['raw3'])} win {r['win3']*100:.1f}% | CAGR gross {g['cagr']*100:5.1f}% net {p['cagr']*100:5.1f}% "
                  f"Sharpe {p['sharpe']:.2f} maxDD {p['max_dd']*100:.0f}% exposure {r['exposure']*100:.0f}%")
    print("\nVERDICT", res["verdict"])


if __name__ == "__main__":
    main()
