"""Pre-registered test 3 (see PREREGISTRATION.md): regime-gated,
risk-budgeted momentum, with ablations and benchmarks, on three samples.
Also prints the strategy's target portfolio as of the latest close.

  python momentum.py   -> results/momentum.json, results/target_portfolio.csv
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
from holdout import holdout_universe, NASDAQ_TO_GICS  # noqa: E402,F401

DATA, OUT = DIP / "data", HERE / "results"
START = pd.Timestamp("2005-01-01")
SAMPLES = {"S&P 2005-15": ("sp", "2005-01-01", "2015-12-31"),
           "S&P 2016-26": ("sp", "2016-01-01", "2100-01-01"),
           "New stocks 2005-26": ("new", "2005-01-01", "2100-01-01")}
NAV_NOW = 23941.0
HOLDINGS_NOW = ["MU", "STX", "META", "ARM", "NVDA", "INTC", "QCOM", "ADI", "PG", "ISRG"]


class Market:
    def __init__(self, px, etf, uni, member: bool):
        p = bt.prepare(px, etf, uni)
        g = p.groupby("ticker", sort=False)
        p["vol20avg"] = g["volume"].transform(lambda s: s.rolling(20, min_periods=15).mean())
        wide = lambda c: p.pivot(index="date", columns="ticker", values=c)
        self.adj = wide("adj_close").ffill()
        self.dates = self.adj.index
        self.tickers = self.adj.columns
        self.adj_v = self.adj.values
        op = wide("aopen").reindex(self.dates)
        self.has_open = op.notna().values
        self.open_ff = op.fillna(self.adj.shift(1)).ffill().values
        self.close_raw = wide("close").reindex(self.dates).values
        self.vol20 = wide("vol20avg").reindex(self.dates).values
        self.member = wide("in_index").reindex(self.dates).fillna(False).astype(bool).values if member else np.ones_like(self.has_open)
        self.alive = wide("adj_close").reindex(self.dates).notna().values
        sec = uni.set_index("ticker")["sector"].reindex(self.tickers).fillna("Other")
        self.sector = sec.values
        self.ret = self.adj.pct_change().values
        spy = etf[etf.ticker == "SPY"].set_index("date")["adj_close"].reindex(self.dates).ffill()
        self.spy = spy.values
        self.spy_up = (spy > spy.rolling(200).mean()).values
        irx = pd.read_parquet(DATA / "irx.parquet")["irx"]
        irx.index = pd.to_datetime(irx.index)
        self.rf = (irx.reindex(self.dates).ffill().fillna(0).values / 100 / 252)
        m = self.dates.month
        self.trade_days = [d for d in range(1, len(self.dates)) if m[d] != m[d - 1]]


def inv_vol_weights(m: Market, s: int, picks: np.ndarray, cap: float) -> np.ndarray:
    r = m.ret[s - 59:s + 1, picks]
    vol = np.nanstd(r, axis=0) * np.sqrt(252)
    vol = np.where(np.isfinite(vol) & (vol > 0), vol, np.nanmedian(vol))
    w = 1 / vol
    w /= w.sum()
    for _ in range(20):  # cap and redistribute
        over = w > cap
        if not over.any():
            break
        excess = (w[over] - cap).sum()
        w[over] = cap
        under = ~over
        w[under] += excess * w[under] / w[under].sum()
    return w


def select(m: Market, s: int, held: np.ndarray, top: int | None, buffer: int | None, sector_cap: int | None):
    mom = m.adj_v[s - 21] / m.adj_v[s - 252] - 1
    elig = (m.close_raw[s] >= 20) & (m.vol20[s] >= 1e6) & m.member[s] & np.isfinite(mom) & m.alive[s] & m.alive[s - 252]
    idx = np.flatnonzero(elig)
    if top is None:
        return idx
    order = idx[np.argsort(-mom[idx], kind="stable")]
    rank = {t: i for i, t in enumerate(order)}
    picks, count = [], {}
    def add(t):
        sct = m.sector[t]
        if sector_cap is not None and count.get(sct, 0) >= sector_cap:
            return False
        picks.append(t); count[sct] = count.get(sct, 0) + 1
        return True
    if buffer:
        for t in sorted([t for t in held if t in rank and rank[t] < buffer], key=lambda t: rank[t]):
            if len(picks) < top:
                add(t)
    for t in order:
        if len(picks) >= top:
            break
        if t not in picks:
            add(t)
    return np.array(picks, dtype=int)


def target_weights(m: Market, s: int, held, cfg) -> tuple[np.ndarray, np.ndarray, float]:
    picks = select(m, s, held, cfg["top"], cfg.get("buffer"), cfg.get("sector_cap"))
    if len(picks) == 0:
        return picks, np.array([]), 0.0
    if cfg.get("weight") == "invvol":
        w = inv_vol_weights(m, s, picks, cfg.get("cap", 0.10))
    else:
        w = np.full(len(picks), 1.0 / len(picks))
    expo = 1.0
    if cfg.get("vol_target"):
        r = np.nan_to_num(m.ret[s - 59:s + 1, picks])
        pv = (r @ w).std() * np.sqrt(252)
        expo = min(1.0, cfg["vol_target"] / pv) if pv > 0 else 1.0
    return picks, w * expo, expo


def simulate(m: Market, cfg: dict, cost_bps: float):
    T = len(m.tickers)
    units = np.zeros(T)
    cash, peak = 1.0, 1.0
    stopped, pending_liq = False, False
    eq = np.empty(len(m.dates))
    traded = 0.0
    c = cost_bps / 1e4
    tset = set(m.trade_days)
    first = int(np.searchsorted(m.dates, START))
    exposure_log = []

    def trade_to(d, target_vals):
        nonlocal units, cash, traded
        px_open = m.open_ff[d]
        cur = np.nan_to_num(units * px_open)
        V = cash + cur.sum()
        diff = np.abs(target_vals - cur).sum()
        cost = diff * c
        scale = (V - cost) / V if V > 0 else 0
        tv = target_vals * scale
        with np.errstate(divide="ignore", invalid="ignore"):
            units = np.where(tv > 0, tv / px_open, 0.0)
        cash = V - cost - tv.sum()
        traded += diff
        return V - cost

    for d in range(len(m.dates)):
        cash *= 1 + m.rf[d]
        if d < first:
            eq[d] = cash
            continue
        if pending_liq:
            trade_to(d, np.zeros(T))
            pending_liq, stopped = False, True
        if d in tset:
            s = d - 1
            V_open = cash + np.nansum(units * m.open_ff[d])
            on = (not cfg.get("regime")) or bool(m.spy_up[s])
            if on and stopped:
                stopped = False
                peak = V_open
            if on and not stopped:
                held = np.flatnonzero(units > 0)
                picks, w, expo = target_weights(m, s, held, cfg)
                picks = picks[m.has_open[d, picks]] if len(picks) else picks
                tv = np.zeros(T)
                if len(picks):
                    w = w[: len(picks)]
                    tv[picks] = V_open * w
                trade_to(d, tv)
                exposure_log.append(float(tv.sum() / V_open) if V_open > 0 else 0.0)
            else:
                trade_to(d, np.zeros(T))
                exposure_log.append(0.0)
        eq[d] = cash + np.nansum(units * m.adj_v[d])
        if cfg.get("stop") and not stopped and units.any():
            peak = max(peak, eq[d])
            if eq[d] / peak - 1 <= -cfg["stop"]:
                pending_liq = True
        elif not stopped:
            peak = max(peak, eq[d])
    e = pd.Series(eq, index=m.dates)
    e = e[e.index >= START]
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    return e / e.iloc[0], traded / yrs / e.mean() * e.iloc[0], float(np.mean(exposure_log)) if exposure_log else 0.0


def spy_regime(m: Market, cost_bps: float):
    """SPY with the same month-end 200-day switch; T-bills when off."""
    c = cost_bps / 1e4
    tset = set(m.trade_days)
    first = int(np.searchsorted(m.dates, START))
    cash, units = 1.0, 0.0
    eq = np.empty(len(m.dates))
    for d in range(len(m.dates)):
        cash *= 1 + m.rf[d]
        if d >= first and d in tset:
            on = bool(m.spy_up[d - 1])
            p = m.spy[d - 1]  # SPY has no open series here: trade at prior close (small simplification)
            V = cash + units * p
            if on and units == 0:
                units = V * (1 - c) / p; cash = 0.0
            elif not on and units > 0:
                cash = V * (1 - c); units = 0.0
        eq[d] = cash + units * m.spy[d]
    e = pd.Series(eq, index=m.dates)
    e = e[e.index >= START]
    return e / e.iloc[0]


def perf(eq: pd.Series, rf: pd.Series, a: str, b: str) -> dict:
    w = eq[(eq.index >= a) & (eq.index <= b)]
    w = w / w.iloc[0]
    r = w.pct_change().dropna()
    x = r - rf.reindex(r.index).fillna(0)
    yrs = (w.index[-1] - w.index[0]).days / 365.25
    dd = w / w.cummax() - 1
    return {"cagr": float(w.iloc[-1] ** (1 / yrs) - 1), "vol": float(r.std() * np.sqrt(252)),
            "sharpe": float(x.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else float("nan"),
            "max_dd": float(dd.min()), "worst_month": float(w.resample("ME").last().pct_change().min())}


CFGS = {
    "A: top-20 momentum, equal weight, always invested": {"top": 20},
    "B: A + market regime switch": {"top": 20, "regime": True},
    "C: B + inverse-vol sizing, sector cap, buffer": {"top": 20, "regime": True, "weight": "invvol", "cap": 0.10, "sector_cap": 5, "buffer": 40},
    "D: full strategy (C + 15% vol target + 20% loss limit)": {"top": 20, "regime": True, "weight": "invvol", "cap": 0.10, "sector_cap": 5, "buffer": 40, "vol_target": 0.15, "stop": 0.20},
    "Equal-weight all eligible stocks, monthly": {"top": None},
}
PRIMARY = "D: full strategy (C + 15% vol target + 20% loss limit)"


def main() -> None:
    etf = pd.read_parquet(DATA / "etf.parquet")
    spx, _, suni = bt.load()
    hpx = pd.read_parquet(DATA / "holdout_prices.parquet")
    huni = holdout_universe()
    mk = {"sp": Market(spx, etf, suni, True), "new": Market(hpx, etf, huni[huni.ticker.isin(hpx.ticker.unique())], False)}
    del spx, hpx
    rf = {u: pd.Series(m.rf, index=m.dates) for u, m in mk.items()}

    res = {"strategies": {}, "spy": {}, "spy_regime": {}}
    spy = etf[etf.ticker == "SPY"].set_index("date")["adj_close"]
    spy = spy[spy.index >= START] / spy[spy.index >= START].iloc[0]
    curves = {}
    for sname, (u, a, b) in SAMPLES.items():
        res["spy"][sname] = perf(spy, rf[u], a, b)
    for cost in (5, 10):
        sr = spy_regime(mk["sp"], cost)
        for sname, (u, a, b) in SAMPLES.items():
            res["spy_regime"].setdefault(sname, {})[f"{cost}bps"] = perf(sr, rf[u], a, b)
        if cost == 5:
            curves["SPY with regime switch"] = sr
    for name, cfg in CFGS.items():
        for cost in (5, 10):
            for u in ("sp", "new"):
                eq, turn, expo = simulate(mk[u], cfg, cost)
                for sname, (uu, a, b) in SAMPLES.items():
                    if uu != u:
                        continue
                    p = perf(eq, rf[u], a, b)
                    p.update({"turnover": turn, "avg_exposure": expo})
                    res["strategies"].setdefault(name, {}).setdefault(sname, {})[f"{cost}bps"] = p
                if cost == 5 and u == "sp" and name in (PRIMARY, "A: top-20 momentum, equal weight, always invested"):
                    curves[name] = eq
    curves["SPY buy & hold"] = spy

    # Verdict for the primary strategy.
    crit = {}
    for sname in SAMPLES:
        p, s = res["strategies"][PRIMARY][sname]["5bps"], res["spy"][sname]
        tb = (1 + pd.Series(mk[SAMPLES[sname][0]].rf, index=mk[SAMPLES[sname][0]].dates)).loc[SAMPLES[sname][1]:SAMPLES[sname][2]]
        tbill_cagr = float(tb.prod() ** (252 / len(tb)) - 1)
        crit[sname] = {"sharpe_beats_spy": p["sharpe"] > s["sharpe"], "dd_smaller_than_spy": p["max_dd"] > s["max_dd"],
                       "cagr_above_tbills": p["cagr"] > tbill_cagr, "tbill_cagr": tbill_cagr}
    res["criteria"] = crit
    res["pass"] = all(all(v for k, v in c.items() if k != "tbill_cagr") for c in crit.values())

    # Yearly returns, primary vs SPY (S&P universe).
    y = pd.DataFrame({k: v.resample("YE").last().pct_change() for k, v in curves.items()})
    y.iloc[0] = pd.Series({k: v.resample("YE").last().iloc[0] - 1 for k, v in curves.items()})
    y.index = y.index.year
    res["yearly"] = y.round(4).to_dict()
    OUT.mkdir(exist_ok=True)
    pd.DataFrame({k: v.resample("W").last() for k, v in curves.items()}).to_csv(OUT / "curves_weekly.csv", float_format="%.5f")

    # Target portfolio as of the latest close (S&P universe, primary rules).
    m = mk["sp"]
    s = len(m.dates) - 1
    cfg = CFGS[PRIMARY]
    on = bool(m.spy_up[s])
    picks, w, expo = target_weights(m, s, np.array([], dtype=int), cfg) if on else (np.array([], int), np.array([]), 0.0)
    mom = m.adj_v[s - 21] / m.adj_v[s - 252] - 1
    vol60 = np.nanstd(m.ret[s - 59:s + 1], axis=0) * np.sqrt(252)
    tp = pd.DataFrame({"ticker": m.tickers[picks], "sector": m.sector[picks], "weight": w,
                       "dollars": w * NAV_NOW, "last_close": m.close_raw[s, picks],
                       "momentum_12_1": mom[picks], "vol_60d": vol60[picks]})
    tp["shares"] = np.floor(tp["dollars"] / tp["last_close"]).astype(int)
    tp = tp.sort_values("weight", ascending=False)
    tp.to_csv(OUT / "target_portfolio.csv", index=False, float_format="%.4f")
    res["target"] = {"as_of": str(m.dates[s].date()), "regime_on": on, "exposure": expo,
                     "spy_vs_200d": float(m.spy[s] / pd.Series(m.spy).rolling(200).mean().iloc[s] - 1),
                     "overlap_with_current": sorted(set(tp.ticker) & set(HOLDINGS_NOW))}
    (OUT / "momentum.json").write_text(json.dumps(res, indent=1, default=float))

    # Console report
    def line(label, p):
        return f"  {label:<58} CAGR {p['cagr']*100:5.1f}%  Sharpe {p['sharpe']:.2f}  maxDD {p['max_dd']*100:5.0f}%  vol {p['vol']*100:4.1f}%"
    for sname in SAMPLES:
        print(f"\n{sname}")
        print(line("SPY buy & hold", res["spy"][sname]))
        print(line("SPY with regime switch (5 bps)", res["spy_regime"][sname]["5bps"]))
        for name in CFGS:
            p = res["strategies"][name][sname]["5bps"]; p10 = res["strategies"][name][sname]["10bps"]
            print(line(name, p) + f"  | 10bps CAGR {p10['cagr']*100:5.1f}%  turnover {p['turnover']:.1f}x  avg exposure {p['avg_exposure']*100:.0f}%")
    print("\nCRITERIA (primary, 5 bps):")
    for sname, c in crit.items():
        print(f"  {sname}: {c}")
    print("PASS" if res["pass"] else "FAIL")
    print("\nYearly returns (S&P universe):")
    print(y.round(3).to_string())
    print(f"\nTARGET as of {res['target']['as_of']}: regime on={on}, SPY vs 200d {res['target']['spy_vs_200d']:+.1%}, exposure {expo:.0%}")
    print(tp.round(3).to_string(index=False))
    print("overlap with current holdings:", res["target"]["overlap_with_current"])


if __name__ == "__main__":
    main()
