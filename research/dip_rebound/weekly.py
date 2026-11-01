"""Pre-registered test 2 (see PREREGISTRATION.md): a lower-turnover weekly
pullback portfolio, 36 variants, judged against SPY on three samples.

Weekly cycle: signal at the week's last close, trade at the next open, hold
until the next week's open. Candidates: volume >= 1M, close >= $20, in the
universe, 5-day return <= -2%. Hold the top N equal weight, rest in cash.
Costs are charged on actual traded value (including re-weighting).

  python weekly.py      -> results/weekly.json, results/weekly.csv
"""

from __future__ import annotations

import json
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

import backtest as bt
from holdout import holdout_universe

HERE = Path(__file__).resolve().parent
DATA, OUT = HERE / "data", HERE / "results"
NS = [10, 20, 50]
RANKS = {"deepest": None, "band 2-10%": -0.10}
FILTERS = ["none", "SPY above 200d", "stock above 200d"]
BUFFERS = [False, True]
COSTS = [5, 10]
SAMPLES = {"S&P 2005-15": ("sp", "2005-01-01", "2015-12-31"),
           "S&P 2016-26": ("sp", "2016-01-01", "2100-01-01"),
           "New stocks 2005-26": ("new", "2005-01-01", "2100-01-01")}


class Market:
    """Wide (date x ticker) matrices for one universe."""

    def __init__(self, px: pd.DataFrame, etf: pd.DataFrame, uni: pd.DataFrame, member: bool):
        p = bt.prepare(px, etf, uni)
        p = p[p["date"] >= pd.Timestamp("2004-12-01")]
        g = p.groupby("ticker", sort=False)
        p["ret5"] = p["adj_close"] / g["adj_close"].shift(5) - 1
        elig = (p["volume"] >= bt.MIN_VOL) & (p["close"] >= bt.MIN_PRICE) & p["prev_aclose"].notna()
        if member:
            elig &= p["in_index"]
        p["elig"] = elig
        p["above200"] = p["adj_close"] > p["sma200"]
        wide = lambda c: p.pivot(index="date", columns="ticker", values=c)
        self.close = wide("adj_close").ffill()
        self.dates = self.close.index
        self.open = wide("aopen").reindex(self.dates)
        self.open_ff = self.open.fillna(self.close.shift(1)).ffill().values
        self.close_v = self.close.values
        self.has_open = self.open.notna().values
        self.elig = wide("elig").reindex(self.dates).fillna(False).astype(bool).values
        self.ret5 = wide("ret5").reindex(self.dates).values
        self.above = wide("above200").reindex(self.dates).fillna(False).astype(bool).values
        spy = p.drop_duplicates("date").set_index("date")["spy_above200"].reindex(self.dates)
        self.spy_up = spy.fillna(False).astype(bool).values
        # Last trading day of each week = signal day; next trading day = trade day.
        wk = pd.Series(self.dates).dt.isocalendar()
        key = wk["year"].astype(str) + "-" + wk["week"].astype(str)
        last = pd.Series(range(len(self.dates))).groupby(key.values).max().sort_values().values
        self.trade_day = {int(s) + 1: int(s) for s in last if s + 1 < len(self.dates)}


def simulate(m: Market, n: int | None, rank_floor: float | None, filt: str, buffer: bool, cost_bps: float):
    T = m.close_v.shape[1]
    units = np.zeros(T)
    cash, eq = 1.0, np.empty(len(m.dates))
    traded = 0.0
    c = cost_bps / 1e4
    for d in range(len(m.dates)):
        s = m.trade_day.get(d)
        if s is not None:
            px_open = m.open_ff[d]
            held_val = np.nan_to_num(units * px_open)
            V = cash + held_val.sum()
            cand = m.elig[s] & m.has_open[d]
            if n is not None:  # pullback strategy; n=None is the all-eligible benchmark
                r5 = m.ret5[s]
                cand &= (r5 <= -0.02)
                if rank_floor is not None:
                    cand &= (r5 >= rank_floor)
                if filt == "SPY above 200d" and not m.spy_up[s]:
                    cand[:] = False
                elif filt == "stock above 200d":
                    cand &= m.above[s]
            idx = np.flatnonzero(cand)
            if n is None:
                pick = idx
                w = np.full(len(pick), 1.0 / max(len(pick), 1))
            else:
                order = idx[np.argsort(m.ret5[s][idx], kind="stable")]
                if buffer:
                    keep_zone = set(order[: 2 * n].tolist())
                    kept = [i for i in np.flatnonzero(units > 0) if i in keep_zone][:n]
                    fill = [i for i in order if i not in set(kept)][: n - len(kept)]
                    pick = np.array(kept + fill, dtype=int)
                else:
                    pick = order[:n]
                w = np.full(len(pick), 1.0 / n)
            target = np.zeros(T)
            target[pick] = V * w
            trade = np.abs(target - held_val).sum()
            cost = trade * c
            V2 = V - cost
            target *= V2 / V if V > 0 else 0
            with np.errstate(divide="ignore", invalid="ignore"):
                units = np.where(target > 0, target / px_open, 0.0)
            cash = V2 - target.sum()
            traded += trade
        eq[d] = cash + np.nansum(units * m.close_v[d])
    e = pd.Series(eq, index=m.dates)
    return e[e.index >= bt.START], traded


def perf_window(eq: pd.Series, a: str, b: str) -> dict:
    w = eq[(eq.index >= a) & (eq.index <= b)]
    return bt.perf(w / w.iloc[0])


def main() -> None:
    etf = pd.read_parquet(DATA / "etf.parquet")
    spx, _, suni = bt.load()
    hpx = pd.read_parquet(DATA / "holdout_prices.parquet")
    huni = holdout_universe()
    mk = {"sp": Market(spx, etf, suni, True), "new": Market(hpx, etf, huni[huni.ticker.isin(hpx.ticker.unique())], False)}
    del spx, hpx
    spy = etf[etf.ticker == "SPY"].set_index("date")["adj_close"]
    spy_perf = {k: perf_window(spy[spy.index >= bt.START], a, b) for k, (_, a, b) in SAMPLES.items()}

    rows = []
    variants = [(None, None, "none", False, "All eligible stocks, weekly (benchmark)")]
    for n, (rname, floor), filt, buf in product(NS, RANKS.items(), FILTERS, BUFFERS):
        variants.append((n, floor, filt, buf, f"Top {n}, {rname}, filter: {filt}, buffer: {'yes' if buf else 'no'}"))
    for n, floor, filt, buf, name in variants:
        row = {"variant": name, "n": n, "filter": filt, "buffer": buf}
        for cost in COSTS:
            cache = {}
            for u in ("sp", "new"):
                cache[u] = simulate(mk[u], n, floor, filt, buf, cost)
            for sname, (u, a, b) in SAMPLES.items():
                eq, traded = cache[u]
                p = perf_window(eq, a, b)
                row[f"{sname} | {cost}bps | cagr"] = p["cagr"]
                row[f"{sname} | {cost}bps | sharpe"] = p["sharpe"]
                row[f"{sname} | {cost}bps | max_dd"] = p["max_dd"]
            yrs = (cache["sp"][0].index[-1] - cache["sp"][0].index[0]).days / 365.25
            row[f"turnover_per_year_sp | {cost}bps"] = cache["sp"][1] / cache["sp"][0].mean() / yrs
        row["pass"] = all(row[f"{s} | 5bps | cagr"] > spy_perf[s]["cagr"] and row[f"{s} | 5bps | sharpe"] > spy_perf[s]["sharpe"]
                          for s in SAMPLES)
        row["samples_beating_spy_5bps"] = sum(row[f"{s} | 5bps | cagr"] > spy_perf[s]["cagr"] and
                                              row[f"{s} | 5bps | sharpe"] > spy_perf[s]["sharpe"] for s in SAMPLES)
        rows.append(row)
        cells = " | ".join(f"{row[f'{s} | 5bps | cagr']*100:5.1f}% S{row[f'{s} | 5bps | sharpe']:.2f}" for s in SAMPLES)
        print(f"{name:<66} {cells} | 10bps S&P16+ {row['S&P 2016-26 | 10bps | cagr']*100:5.1f}% | "
              f"turnover {row['turnover_per_year_sp | 5bps']:5.1f}x/yr | beats SPY in {row['samples_beating_spy_5bps']}/3"
              + ("  PASS" if row["pass"] else ""), flush=True)

    df = pd.DataFrame(rows)
    OUT.mkdir(exist_ok=True)
    df.to_csv(OUT / "weekly.csv", index=False, float_format="%.6f")
    json.dump({"spy": spy_perf, "variants": rows, "passing": df.loc[df["pass"], "variant"].tolist()},
              open(OUT / "weekly.json", "w"), indent=1, default=float)
    print("\nSPY buy & hold: " + " | ".join(f"{s} {p['cagr']*100:.1f}% Sharpe {p['sharpe']:.2f} maxDD {p['max_dd']*100:.0f}%" for s, p in spy_perf.items()))
    print(f"PASSING variants: {int(df['pass'].sum())} of {len(df) - 1}")


if __name__ == "__main__":
    main()
