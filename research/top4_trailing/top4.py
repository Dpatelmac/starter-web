"""Pre-registered test 8 (see PREREGISTRATION.md): each day take the 10
biggest S&P 500 decliners, buy the top 4 at the next open (ranked by the
deepest next-open gap), exit only by a trailing stop. Up to 50 positions of
2% each. Controls: random 4 of the same 10, and the 4 biggest drops.

  python top4.py   -> results/top4.json, results/trades_primary.csv
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
START = pd.Timestamp("2005-01-01")
TRAILS = {"3%": 0.03, "5%": 0.05, "8%": 0.08, "2x ATR": "atr"}
RANKS = ["gap", "drop", "random"]
SEEDS = [1, 2, 3, 4, 5]
SIZE, MAX_POS, TOP_N, PICKS = 0.02, 50, 10, 4
COST, STOP_SLIP = 5 / 1e4, 10 / 1e4


class Market:
    def __init__(self, px, etf, uni, membership: str):
        p = bt.prepare(px, etf, uni)
        if membership == "sp500":
            added = uni.set_index("ticker")["sp500_added"]
            p["in_index"] = p["date"] >= p["ticker"].map(added)
        elif membership == "none":
            p["in_index"] = True
        tr = pd.concat([p["ahigh"] - p["alow"], (p["ahigh"] - p["prev_aclose"]).abs(), (p["alow"] - p["prev_aclose"]).abs()], axis=1).max(axis=1)
        p["atr14"] = tr.groupby(p["ticker"]).transform(lambda s: s.ewm(alpha=1 / 14, adjust=False).mean())
        p["elig"] = (p["volume"] >= bt.MIN_VOL) & (p["close"] >= bt.MIN_PRICE) & p["prev_aclose"].notna() & p["in_index"].astype(bool)
        W = lambda c: p.pivot(index="date", columns="ticker", values=c)
        close = W("adj_close")
        self.dates = close.index
        self.tk = close.columns
        self.alive = close.notna().values
        self.c = close.ffill().values
        self.o = W("aopen").reindex(self.dates).values
        self.h = W("ahigh").reindex(self.dates).values
        self.l = W("alow").reindex(self.dates).values
        self.ret = W("ret").reindex(self.dates).values
        self.atrp = (W("atr14") / close).reindex(self.dates).values
        self.elig = W("elig").reindex(self.dates).fillna(False).astype(bool).values
        irx = pd.read_parquet(DIP / "data" / "irx.parquet")["irx"]
        irx.index = pd.to_datetime(irx.index)
        self.rf = (irx.reindex(self.dates).ffill().fillna(0) / 100 / 252).values
        # Daily top-10 decliners (down >= 2%), by drop.
        self.top10 = []
        for s in range(len(self.dates)):
            r = np.where(self.elig[s] & (self.ret[s] <= -0.02), self.ret[s], np.nan)
            idx = np.flatnonzero(np.isfinite(r))
            self.top10.append(idx[np.argsort(r[idx])][:TOP_N] if len(idx) else idx)


def simulate(m: Market, trail, rank: str, seed: int = 0, stop_slip: float = STOP_SLIP):
    rng = np.random.default_rng(seed)
    n = len(m.dates)
    first = int(np.searchsorted(m.dates, START))
    cash = 1.0
    pos = {}  # ticker index -> dict(units, entry, hwm, trail, d0)
    eq = np.ones(n)
    trades, expo = [], []

    def sell(t, price, d, slip):
        nonlocal cash
        p = pos.pop(t)
        cash += p["units"] * price * (1 - COST - slip)
        trades.append((m.dates[p["d0"]], m.dates[d], m.tk[t], p["entry"], price, price * (1 - COST - slip) / (p["entry"] * (1 + COST)) - 1, d - p["d0"] + 1))

    for d in range(n):
        cash *= 1 + m.rf[d]
        if d <= first:
            eq[d] = cash
            continue
        # 0. Stocks that vanished (delisted): sell at last close.
        for t in [t for t in pos if not m.alive[d, t]]:
            sell(t, m.c[d, t], d, 0.0)
        # 1. Gap through the stop: sell at the open.
        for t in list(pos):
            p = pos[t]
            stop = p["hwm"] * (1 - p["trail"])
            if np.isfinite(m.o[d, t]) and m.o[d, t] <= stop:
                sell(t, m.o[d, t], d, stop_slip)
        # 2. New buys at the open from yesterday's top-10 decliners.
        s = d - 1
        cands = [t for t in m.top10[s] if t not in pos and np.isfinite(m.o[d, t]) and m.o[d, t] / m.c[s, t] - 1 < 0.015]
        if cands:
            gap = np.array([m.o[d, t] / m.c[s, t] - 1 for t in cands])
            if rank == "gap":
                order = np.lexsort((np.array([m.ret[s, t] for t in cands]), gap))
            elif rank == "drop":
                order = np.argsort([m.ret[s, t] for t in cands])
            else:
                order = rng.permutation(len(cands))
            equity = cash + sum(p["units"] * m.o[d, t] if np.isfinite(m.o[d, t]) else p["units"] * m.c[s, t] for t, p in pos.items())
            for i in order[:PICKS]:
                t = cands[i]
                amt = SIZE * equity
                if len(pos) >= MAX_POS or cash < amt:
                    break
                tr = trail if trail != "atr" else float(np.clip(2 * m.atrp[s, t], 0.01, 0.5)) if np.isfinite(m.atrp[s, t]) else 0.05
                px = m.o[d, t]
                pos[t] = {"units": amt / (px * (1 + COST)), "entry": px, "hwm": px, "trail": tr, "d0": d}
                cash -= amt
        # 3. Intraday stop hits (including today's new buys).
        for t in list(pos):
            p = pos[t]
            stop = p["hwm"] * (1 - p["trail"])
            if np.isfinite(m.l[d, t]) and m.l[d, t] <= stop:
                sell(t, stop, d, stop_slip)
        # 4. Close: mark to market and raise the high-water mark.
        inv = 0.0
        for t, p in pos.items():
            inv += p["units"] * m.c[d, t]
            if m.alive[d, t]:
                p["hwm"] = max(p["hwm"], m.c[d, t])
        eq[d] = cash + inv
        expo.append(inv / eq[d] if eq[d] > 0 else 0)
    e = pd.Series(eq, index=m.dates).loc[START:]
    tr = pd.DataFrame(trades, columns=["entry_date", "exit_date", "ticker", "entry", "exit", "ret_net", "days"])
    return e / e.iloc[0], tr, float(np.mean(expo))


def perf(eq: pd.Series, a, b, rf: pd.Series) -> dict:
    w = eq.loc[a:b]
    w = w / w.iloc[0]
    r = w.pct_change().dropna()
    x = r - rf.reindex(r.index).fillna(0)
    yrs = (w.index[-1] - w.index[0]).days / 365.25
    mo = w.resample("ME").last().pct_change().dropna()
    return {"cagr": float(w.iloc[-1] ** (1 / yrs) - 1), "sharpe": float(x.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else float("nan"),
            "max_dd": float((w / w.cummax() - 1).min()), "month_win": float((mo > 0).mean()), "vol": float(r.std() * np.sqrt(252))}


def trade_stats(tr: pd.DataFrame, a, b) -> dict:
    t = tr[(tr["entry_date"] >= a) & (tr["entry_date"] <= b)]
    if not len(t):
        return {}
    yrs = (pd.Timestamp(min(b, "2026-10-30")) - pd.Timestamp(a)).days / 365.25
    w, l = t[t.ret_net > 0], t[t.ret_net <= 0]
    return {"trades": int(len(t)), "per_year": float(len(t) / yrs), "win_rate": float(len(w) / len(t)),
            "avg_win": float(w.ret_net.mean()) if len(w) else 0.0, "avg_loss": float(l.ret_net.mean()) if len(l) else 0.0,
            "avg_trade": float(t.ret_net.mean()), "avg_days": float(t.days.mean()), "median_days": float(t.days.median()),
            "same_day_stops": float((t.days == 1).mean())}


SAMPLES = {"S&P 500 2005-15": ("sp500", "2005-01-01", "2015-12-31"), "S&P 500 2016-26": ("sp500", "2016-01-01", "2026-12-31"),
           "S&P 400 2005-26": ("sp400", "2005-01-01", "2026-12-31"), "New stocks 2005-26": ("new", "2005-01-01", "2026-12-31")}


def main() -> None:
    etf = pd.read_parquet(DIP / "data" / "etf.parquet")
    irx = pd.read_parquet(DIP / "data" / "irx.parquet")["irx"]
    irx.index = pd.to_datetime(irx.index)
    rf = irx / 100 / 252
    px, _, uni = bt.load()
    u5, u4 = uni[uni["index"] == "SP500"], uni[uni["index"] == "SP400"]
    hpx = pd.read_parquet(DIP / "data" / "holdout_prices.parquet")
    huni = holdout_universe()
    M = {"sp500": Market(px[px.ticker.isin(u5.ticker)], etf, u5, "sp500"),
         "sp400": Market(px[px.ticker.isin(u4.ticker)], etf, u4, "sp400"),
         "new": Market(hpx, etf, huni[huni.ticker.isin(hpx.ticker.unique())], "none")}
    del px, hpx
    spy = etf[etf.ticker == "SPY"].set_index("date")["adj_close"]
    res = {"spy": {s: perf(spy, a, b, rf) for s, (_, a, b) in SAMPLES.items()}, "runs": {}}

    def run(label, trail, rank, slip=STOP_SLIP, keep_trades=False):
        out = {}
        for u, m in M.items():
            if rank == "random":
                sims = [simulate(m, trail, "random", sd, slip) for sd in SEEDS]
                eq = pd.concat([x[0] for x in sims], axis=1).mean(axis=1)
                tr = pd.concat([x[1] for x in sims]); ex = float(np.mean([x[2] for x in sims]))
            else:
                eq, tr, ex = simulate(m, trail, rank, 0, slip)
            if keep_trades and u == "sp500":
                tr.to_csv(OUT / "trades_primary.csv", index=False, float_format="%.5f")
            for s, (uu, a, b) in SAMPLES.items():
                if uu == u:
                    out[s] = {**perf(eq, a, b, rf), **trade_stats(tr, a, b), "exposure": ex}
        res["runs"][label] = out
        return out

    OUT.mkdir(exist_ok=True)
    for tname, trail in TRAILS.items():
        for rank in RANKS:
            run(f"{tname} trail | {rank}", trail, rank, keep_trades=(tname == "3%" and rank == "gap"))
    run("3% trail | gap | stress 20bps stop slippage", 0.03, "gap", slip=20 / 1e4)

    P = res["runs"]["3% trail | gap"]; Rn = res["runs"]["3% trail | random"]
    crit = {}
    for s in SAMPLES:
        tb = (1 + rf.loc[SAMPLES[s][1]:SAMPLES[s][2]]).prod() ** (252 / len(rf.loc[SAMPLES[s][1]:SAMPLES[s][2]])) - 1
        crit[s] = {"sharpe_beats_spy": bool(P[s]["sharpe"] > res["spy"][s]["sharpe"]), "dd_smaller_than_spy": bool(P[s]["max_dd"] > res["spy"][s]["max_dd"]),
                   "cagr_above_tbills": bool(P[s]["cagr"] > tb), "beats_random_sharpe": bool(P[s]["sharpe"] > Rn[s]["sharpe"])}
    res["criteria"] = crit
    res["pass"] = all(all(v.values()) for v in crit.values())
    (OUT / "top4.json").write_text(json.dumps(res, indent=1, default=float))

    print("SPY:", {s: (round(v["cagr"] * 100, 1), round(v["sharpe"], 2), round(v["max_dd"] * 100)) for s, v in res["spy"].items()})
    for label, blk in res["runs"].items():
        print(f"\n{label}")
        for s, v in blk.items():
            print(f"  {s:<19} CAGR {v['cagr']*100:5.1f}%  Sharpe {v['sharpe']:5.2f}  maxDD {v['max_dd']*100:4.0f}%  months+ {v['month_win']*100:3.0f}%  "
                  f"| trades/yr {v.get('per_year',0):5.0f}  win {v.get('win_rate',0)*100:4.1f}%  avg win {v.get('avg_win',0)*100:+.2f}%  avg loss {v.get('avg_loss',0)*100:+.2f}%  "
                  f"avg trade {v.get('avg_trade',0)*100:+.2f}%  days {v.get('avg_days',0):4.1f}  same-day stop {v.get('same_day_stops',0)*100:3.0f}%  exposure {v['exposure']*100:3.0f}%")
    print("\nCRITERIA:", json.dumps(crit, indent=1)); print("PASS" if res["pass"] else "FAIL")


if __name__ == "__main__":
    main()
