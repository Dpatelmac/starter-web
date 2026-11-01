"""Dip-rebound backtest: do large/mid-cap US stocks that fall >2% on heavy
volume bounce over the next 1-3 sessions?

Signal (day t, known at the close):
  - close-to-close return <= -2%
  - volume >= 1M shares
  - raw (unadjusted) close >= $20
  - stock is in the S&P 500 or S&P 400 on day t (point-in-time, see membership())
Trade: buy at the NEXT open (t+1), the earliest an evening workflow can act;
sell at the close of t+h for h in {1, 2, 3, 5}.

Every result is compared with a baseline: the same stocks, same filters, same
entry/exit timing, on ALL days (not just dips). A dip "edge" is only real if
it beats what these stocks do on an ordinary day.

Statistics are date-clustered: signals on the same day are averaged into one
basket return first, then the t-stat is taken across days. Same-day signals
are highly correlated, so counting them as independent would overstate
significance.

Outputs: results/results.json (all tables and curves for the report) and
results/events.csv.gz (one row per signal).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
OUT = HERE / "results"

START = pd.Timestamp("2005-01-01")
IS_END = pd.Timestamp("2015-12-31")  # 2005-2015 in-sample, 2016+ out-of-sample
DROP = -0.02
MIN_VOL = 1_000_000
MIN_PRICE = 20.0
HOLDS = [1, 2, 3, 5]
COST_BPS_SIDE = 5.0  # per side: commission + slippage on liquid names at the open

SECTOR_ETF = {
    "Information Technology": "XLK", "Health Care": "XLV", "Financials": "XLF",
    "Consumer Discretionary": "XLY", "Consumer Staples": "XLP", "Industrials": "XLI",
    "Energy": "XLE", "Utilities": "XLU", "Real Estate": "XLRE", "Materials": "XLB",
    "Communication Services": "XLC",
}


# ----------------------------------------------------------------------------- data
def load() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    px = pd.read_parquet(DATA / "prices.parquet")
    etf = pd.read_parquet(DATA / "etf.parquet")
    uni = pd.read_csv(DATA / "universe.csv", parse_dates=["sp500_added"])
    return px, etf, uni


def membership(uni: pd.DataFrame) -> pd.Series:
    """Earliest date we can confirm each ticker was in the S&P 500 or 400.

    - S&P 500 members: Wikipedia "Date added".
    - S&P 400 change log (2012 onward): the date a ticker was added to the 400.
    - S&P 400 members with no add record joined before the log starts (2012),
      so they are treated as members throughout. That part is not fully
      point-in-time and is a known residual bias.
    Takes the earliest of the available dates.
    """
    ch = pd.read_csv(DATA / "sp400_changes.csv", parse_dates=["date"])
    add400 = ch.dropna(subset=["added"]).groupby("added")["date"].min()
    d = pd.Series(pd.NaT, index=uni["ticker"].values, dtype="datetime64[ns]")
    d[:] = uni["sp500_added"].values
    for t, dt in add400.items():
        if t in d.index and (pd.isna(d[t]) or dt < d[t]):
            d[t] = dt
    is400 = uni.set_index("ticker")["index"].eq("SP400")
    no_record = is400 & d.isna()
    d[no_record[no_record].index] = pd.Timestamp("1900-01-01")
    return d.fillna(pd.Timestamp("1900-01-01"))


def prepare(px: pd.DataFrame, etf: pd.DataFrame, uni: pd.DataFrame) -> pd.DataFrame:
    px = px.sort_values(["ticker", "date"]).reset_index(drop=True)
    f = px["adj_close"] / px["close"]
    px["aopen"] = px["open"] * f
    px["ahigh"] = px["high"] * f
    px["alow"] = px["low"] * f
    g = px.groupby("ticker", sort=False)

    px["prev_aclose"] = g["adj_close"].shift(1)
    px["ret"] = px["adj_close"] / px["prev_aclose"] - 1
    px["gap"] = px["aopen"] / px["prev_aclose"] - 1  # day t's own opening gap
    px["sma200"] = g["adj_close"].transform(lambda s: s.rolling(200, min_periods=200).mean())
    px["vol20"] = g["volume"].transform(lambda s: s.shift(1).rolling(20, min_periods=20).mean())
    px["rvol"] = px["volume"] / px["vol20"]
    px["ret5_prior"] = g["adj_close"].shift(1) / g["adj_close"].shift(6) - 1  # 5 days BEFORE t
    rng = (px["ahigh"] - px["alow"]).replace(0, np.nan)
    px["close_loc"] = (px["adj_close"] - px["alow"]) / rng  # 0 = closed at low, 1 = at high

    # Forward path: entry at next open, daily marks through t+h.
    px["entry"] = g["aopen"].shift(-1)
    px["next_gap"] = px["entry"] / px["adj_close"] - 1  # overnight gap you'd eat
    for h in range(1, max(HOLDS) + 1):
        px[f"c{h}"] = g["adj_close"].shift(-h)
    for h in HOLDS:
        px[f"r{h}"] = px[f"c{h}"] / px["entry"] - 1

    # Market / sector context.
    e = etf.sort_values(["ticker", "date"]).copy()
    eg = e.groupby("ticker")
    e["eret"] = e["adj_close"] / eg["adj_close"].shift(1) - 1
    e["eentry"] = eg["open"].shift(-1) * (e["adj_close"] / e["close"])
    for h in HOLDS:
        e[f"er{h}"] = eg["adj_close"].shift(-h) / e["eentry"] - 1
    spy = e[e.ticker == "SPY"].set_index("date")
    spy_fwd = {f"spy_c{k}": spy["adj_close"].shift(-k) for k in range(1, max(HOLDS) + 1)}
    spy_sma = spy["adj_close"].rolling(200).mean()
    vix = e[e.ticker == "^VIX"].set_index("date")["close"]

    px = px.merge(
        pd.DataFrame({
            "spy_ret": spy["eret"],
            "spy_above200": spy["adj_close"] > spy_sma,
            "vix": vix,
            **{f"spy_r{h}": spy[f"er{h}"] for h in HOLDS},
            "spy_entry": spy["eentry"], **spy_fwd,
        }).reset_index(),
        on="date", how="left",
    )

    sec = uni.set_index("ticker")["sector"]
    px["sector"] = px["ticker"].map(sec)
    px["sector_etf"] = px["sector"].map(SECTOR_ETF)
    eret = e.pivot(index="date", columns="ticker", values="eret")
    look = eret.stack().rename("sector_ret").reset_index().rename(columns={"ticker": "sector_etf"})
    px = px.merge(look, on=["date", "sector_etf"], how="left")
    px["sector_ret"] = px["sector_ret"].fillna(px["spy_ret"])  # XLRE pre-2015, XLC pre-2018

    px["in_index"] = px["date"] >= px["ticker"].map(membership(uni))
    return px


# ----------------------------------------------------------------------------- stats
def tagged(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["trend"] = np.where(df["adj_close"] > df["sma200"], "Above 200-day avg", "Below 200-day avg")
    df.loc[df["sma200"].isna(), "trend"] = "n/a"
    df["drop_bucket"] = pd.cut(df["ret"], [-1, -0.10, -0.05, -0.03, -0.02],
                               labels=["Worse than -10%", "-5% to -10%", "-3% to -5%", "-2% to -3%"])
    df["gap_type"] = np.where(df["gap"] <= -0.02, "Gapped down 2%+ at open (overnight news)",
                              "Sold off during the day")
    df["sector_type"] = pd.cut(df["sector_ret"], [-1, -0.01, -0.0025, 1],
                               labels=["Sector ETF down 1%+ (sector-wide)", "Sector ETF down 0.25-1%",
                                       "Sector ETF flat/up (stock-specific)"])
    df["rvol_bucket"] = pd.cut(df["rvol"], [0, 1.5, 3, np.inf],
                               labels=["Under 1.5x normal volume", "1.5-3x normal volume", "Over 3x normal volume"])
    df["vix_bucket"] = pd.cut(df["vix"], [0, 15, 20, 30, np.inf],
                              labels=["VIX under 15", "VIX 15-20", "VIX 20-30", "VIX over 30"])
    df["spy_day"] = pd.cut(df["spy_ret"], [-1, -0.01, 0.0025, 1],
                           labels=["S&P down 1%+", "S&P roughly flat", "S&P up 0.25%+"])
    df["close_bucket"] = pd.cut(df["close_loc"], [-0.01, 0.2, 0.6, 1.01],
                                labels=["Closed near day's low", "Closed mid-range", "Closed near day's high"])
    df["prior5"] = pd.cut(df["ret5_prior"], [-1, -0.05, 0.0, 0.05, 10],
                          labels=["Down 5%+ in prior 5 days", "Down 0-5% prior 5 days",
                                  "Up 0-5% prior 5 days", "Up 5%+ prior 5 days"])
    df["market_trend"] = np.where(df["spy_above200"], "S&P above its 200-day avg", "S&P below its 200-day avg")
    df["period"] = np.where(df["date"] <= IS_END, "2005-2015 (in-sample)", "2016-2026 (out-of-sample)")
    df["year"] = df["date"].dt.year
    return df


def add_edge(ev: pd.DataFrame, base: pd.DataFrame) -> pd.DataFrame:
    """x{h} = signal return minus the average return of ALL eligible stocks
    bought at the same open and sold at the same close. This removes market
    moves: on a crash-rebound day every stock bounces, and that is beta, not
    a dip edge."""
    ev = ev.copy()
    for h in HOLDS:
        u = base.groupby("date")[f"r{h}"].mean()
        ev[f"x{h}"] = ev[f"r{h}"] - ev["date"].map(u)
    return ev


def clustered(df: pd.DataFrame, col: str) -> tuple[float, float]:
    """Average by date first (one basket per day), then mean / t-stat across days."""
    daily = df.groupby("date")[col].mean().dropna()
    n = len(daily)
    if n < 2 or daily.std(ddof=1) == 0:
        return float(daily.mean()) if n else float("nan"), float("nan")
    return float(daily.mean()), float(daily.mean() / daily.std(ddof=1) * np.sqrt(n))


def summarize(ev: pd.DataFrame) -> dict:
    out = {"n": int(len(ev)), "days": int(ev["date"].nunique())}
    for h in HOLDS:
        r = ev[f"r{h}"]
        daily_mean, _ = clustered(ev, f"r{h}")
        d = {"mean": float(r.mean()), "median": float(r.median()), "win": float((r > 0).mean()),
             "daily_mean": daily_mean}
        if f"x{h}" in ev.columns:
            edge, t = clustered(ev, f"x{h}")
            d.update({"edge": edge, "t": t, "edge_event": float(ev[f"x{h}"].mean()),
                      "beat_univ": float((ev[f"x{h}"] > 0).mean())})
        out[f"h{h}"] = d
    out["next_gap_mean"] = float(ev["next_gap"].mean())
    out["next_gap_bad"] = float((ev["next_gap"] <= -0.02).mean())
    return out


def by(ev: pd.DataFrame, col: str, min_n: int = 50) -> list[dict]:
    rows = []
    for k, sub in ev.groupby(col, observed=True, sort=True):
        if len(sub) < min_n:
            continue
        s = summarize(sub)
        s["bucket"] = str(k)
        rows.append(s)
    return rows


# Single conditions the rule search can combine (all known at day t's close).
CONDITIONS = {
    "Prior 5 days down 5%+": lambda d: d["ret5_prior"] <= -0.05,
    "Prior 5 days down": lambda d: d["ret5_prior"] < 0,
    "Drop 3%+": lambda d: d["ret"] <= -0.03,
    "Drop 5-10%": lambda d: (d["ret"] <= -0.05) & (d["ret"] > -0.10),
    "No gap-down (sold off intraday)": lambda d: d["gap"] > -0.02,
    "Closed near day's low": lambda d: d["close_loc"] <= 0.2,
    "Sector ETF down 1%+": lambda d: d["sector_ret"] <= -0.01,
    "Stock-specific (sector flat/up)": lambda d: d["sector_ret"] > -0.0025,
    "VIX 20+": lambda d: d["vix"] >= 20,
    "VIX under 20": lambda d: d["vix"] < 20,
    "Stock above 200-day avg": lambda d: d["adj_close"] > d["sma200"],
    "Stock below 200-day avg": lambda d: d["adj_close"] <= d["sma200"],
    "S&P above 200-day avg": lambda d: d["spy_above200"].astype(bool),
    "Volume 1.5x+ normal": lambda d: d["rvol"] >= 1.5,
}


def rule_search(ev: pd.DataFrame, hold: int = 3, min_days: int = 300) -> list[dict]:
    """Score every single condition and every pair on 2005-2015 ONLY, then
    report how each does on 2016-2026. The out-of-sample column is the honest
    one; the in-sample ranking is how a researcher would have chosen."""
    from itertools import combinations
    is_ev = ev[ev["date"] <= IS_END]
    oos_ev = ev[ev["date"] > IS_END]
    masks_is = {k: f(is_ev).fillna(False).values for k, f in CONDITIONS.items()}
    masks_oos = {k: f(oos_ev).fillna(False).values for k, f in CONDITIONS.items()}
    rules = [(k,) for k in CONDITIONS] + list(combinations(CONDITIONS, 2))
    rows = []
    col = f"x{hold}"
    for rule in rules:
        m_is = np.logical_and.reduce([masks_is[k] for k in rule])
        m_oos = np.logical_and.reduce([masks_oos[k] for k in rule])
        a, b = is_ev[m_is], oos_ev[m_oos]
        if a["date"].nunique() < min_days or b["date"].nunique() < min_days:
            continue
        e_is, t_is = clustered(a, col)
        e_oos, t_oos = clustered(b, col)
        rows.append({"rule": " + ".join(rule), "parts": list(rule),
                     "n_is": int(len(a)), "edge_is": e_is, "t_is": t_is,
                     "n_oos": int(len(b)), "edge_oos": e_oos, "t_oos": t_oos,
                     "raw_oos": clustered(b, f"r{hold}")[0], "win_oos": float((b[f"r{hold}"] > 0).mean())})
    rows.sort(key=lambda r: -r["t_is"])
    return rows


def rule_mask(df: pd.DataFrame, parts: list[str]) -> pd.Series:
    return np.logical_and.reduce([CONDITIONS[k](df).fillna(False).values for k in parts])


# ----------------------------------------------------------------------------- portfolio
def simulate(ev: pd.DataFrame, px: pd.DataFrame, dates: pd.DatetimeIndex, hold: int,
             cost_bps: float = COST_BPS_SIDE, min_slots: int = 5, max_names: int | None = None,
             rank_col: str = "ret", hedge: bool = False) -> pd.Series:
    """Daily equity curve of a rolling-sleeve strategy.

    Capital is split into `hold` sleeves. On each signal day a free sleeve buys
    that day's signals at the next open, equal weight with each name getting
    1/max(n, min_slots) of the sleeve (the rest stays in cash, so one lonely
    signal never takes the whole sleeve), and sells them at the close `hold`
    days later. Costs are charged on entry and exit.

    hedge=True shorts the same dollar amount of SPY over the same window, so
    the curve shows only the stock-specific part of the return.
    """
    pos = {d: i for i, d in enumerate(dates)}
    ev = ev[ev["date"].isin(pos)].copy()
    if max_names:
        ev = ev.sort_values(rank_col).groupby("date").head(max_names)
    # Per-event daily value path v_1..v_hold, starting from 1 at the entry open.
    cols = [f"c{k}" for k in range(1, hold + 1)]
    path = ev[cols].div(ev["entry"], axis=0)
    path = path.where(path.notna()).ffill(axis=1)  # delisted mid-hold: carry last mark
    if hedge:
        spath = ev[[f"spy_c{k}" for k in range(1, hold + 1)]].div(ev["spy_entry"], axis=0)
        path = 1 + path - spath.values
    ev = ev.assign(**{f"v{k}": path[c].values for k, c in zip(range(1, hold + 1), cols)})
    cohorts = {}
    for d, sub in ev.groupby("date"):
        w = 1.0 / max(len(sub), min_slots)
        invested = w * len(sub)
        vals = [1 - invested + w * sub[f"v{k}"].sum() for k in range(1, hold + 1)]
        cohorts[pos[d]] = (np.array(vals), invested)

    n = len(dates)
    sleeves = np.full(hold, 1.0 / hold)
    daily = np.zeros(n)
    marks = [None] * hold  # (start_index, entry_capital, path)
    cost = cost_bps / 1e4
    for i in range(n):
        s = i % hold
        # Sleeve s is free at the close of day i: settle and look for a new cohort.
        if marks[s] is not None:
            start, cap, vals, inv = marks[s]
            sleeves[s] = cap * vals[-1] - cap * inv * cost
            marks[s] = None
        if i in cohorts and i + hold < n:
            vals, inv = cohorts[i]
            cap = sleeves[s] * (1 - inv * cost)
            marks[s] = (i, cap, vals, inv)
        # Mark every sleeve at today's close.
        total = 0.0
        for j in range(hold):
            if marks[j] is not None and marks[j][0] < i:
                start, cap, vals, inv = marks[j]
                total += cap * vals[min(i - start, hold) - 1]
            elif marks[j] is not None:
                total += marks[j][1]
            else:
                total += sleeves[j]
        daily[i] = total
    return pd.Series(daily, index=dates)


def perf(eq: pd.Series) -> dict:
    r = eq.pct_change().dropna()
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    dd = eq / eq.cummax() - 1
    return {
        "cagr": float(eq.iloc[-1] ** (1 / yrs) - 1),
        "vol": float(r.std() * np.sqrt(252)),
        "sharpe": float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else np.nan,
        "max_dd": float(dd.min()),
        "total": float(eq.iloc[-1] - 1),
        "worst_day": float(r.min()),
    }


# ----------------------------------------------------------------------------- main
SPLITS = {
    "period": "Period", "trend": "Stock vs its 200-day average", "drop_bucket": "Size of the drop",
    "gap_type": "How it fell", "sector_type": "Sector-wide vs stock-specific",
    "rvol_bucket": "Volume vs 20-day average", "vix_bucket": "Fear level (VIX)",
    "spy_day": "What the S&P did that day", "market_trend": "Market trend",
    "close_bucket": "Where it closed in the day's range", "prior5": "Prior 5 days",
}


def weekly(eq: pd.Series) -> dict:
    w = eq.resample("W").last()
    return {"dates": [d.strftime("%Y-%m-%d") for d in w.index], "values": [round(float(x), 4) for x in w.values]}


def main() -> None:
    OUT.mkdir(exist_ok=True)
    px, etf, uni = load()
    px = prepare(px, etf, uni)
    px = px[(px["date"] >= START) & px["entry"].notna() & px["r1"].notna()]

    elig = (px["volume"] >= MIN_VOL) & (px["close"] >= MIN_PRICE) & px["prev_aclose"].notna()
    base = tagged(px[elig & px["in_index"]])
    ev = add_edge(base[base["ret"] <= DROP], base)
    ev_nopit = add_edge(tagged(px[elig & (px["ret"] <= DROP)]), tagged(px[elig]))

    res: dict = {"params": {
        "start": str(START.date()), "end": str(px["date"].max().date()), "drop": DROP,
        "min_vol": MIN_VOL, "min_price": MIN_PRICE, "holds": HOLDS, "cost_bps_side": COST_BPS_SIDE,
        "universe_size": int(uni.shape[0]), "is_end": str(IS_END.date()),
    }}
    res["overall"] = summarize(ev)
    res["baseline"] = summarize(base)
    res["no_pit"] = summarize(ev_nopit)

    res["splits"] = {}
    for col, title in SPLITS.items():
        res["splits"][col] = {
            "title": title, "rows": by(ev, col),
            "by_period": {p: by(sub, col) for p, sub in ev.groupby("period")},
        }

    res["by_year"] = []
    for y, sub in ev.groupby("year"):
        e3, t3 = clustered(sub, "x3")
        res["by_year"].append({"year": int(y), "n": int(len(sub)), "r3": float(sub["r3"].mean()),
                               "base_r3": float(base.loc[base["year"] == y, "r3"].mean()),
                               "edge3": e3, "t3": t3, "win3": float((sub["r3"] > 0).mean())})

    # Rule search: choose on 2005-2015, judge on 2016-2026.
    rules = rule_search(ev, hold=3)
    res["rules"] = rules[:40]
    best = rules[0]
    res["best_rule"] = best
    best_ev = ev[rule_mask(ev, best["parts"])]
    res["best_summary"] = summarize(best_ev)
    res["best_by_period"] = by(best_ev, "period")
    res["best_by_year"] = []
    for y, sub in best_ev.groupby("year"):
        e3, t3 = clustered(sub, "x3")
        res["best_by_year"].append({"year": int(y), "n": int(len(sub)), "edge3": e3, "t3": t3,
                                    "r3": float(sub["r3"].mean()), "win3": float((sub["r3"] > 0).mean())})

    # Portfolio simulations (gross and net of costs, plain and SPY-hedged).
    dates = pd.DatetimeIndex(sorted(px["date"].unique()))
    spy = etf[etf.ticker == "SPY"].set_index("date")["adj_close"].reindex(dates).ffill()
    spy_eq = spy / spy.iloc[0]
    oos = dates > IS_END
    port, curves = {}, {"SPY buy & hold": spy_eq}

    def run(name, sub, hold, cost, hedge=False, curve=False):
        eq = simulate(sub, px, dates, hold, cost_bps=cost, hedge=hedge)
        port[name] = {"full": perf(eq), "oos": perf(eq[oos] / eq[oos].iloc[0]), "hold": hold,
                      "cost_bps_side": cost, "hedged": hedge}
        if curve:
            curves[name] = eq

    port["SPY buy & hold"] = {"full": perf(spy_eq), "oos": perf(spy_eq[oos] / spy_eq[oos].iloc[0]),
                              "hold": None, "cost_bps_side": 0, "hedged": False}
    for h in [1, 3, 5]:
        run(f"All dips, {h}d hold, no costs", ev, h, 0)
        run(f"All dips, {h}d hold, 5 bps/side", ev, h, 5, curve=(h == 3))
    run("All dips, 3d hold, hedged, 5 bps/side", ev, 3, 5, hedge=True)
    for h in [3, 5]:
        run(f"Best rule, {h}d hold, no costs", best_ev, h, 0)
        run(f"Best rule, {h}d hold, 5 bps/side", best_ev, h, 5, curve=(h == 5))
        run(f"Best rule, {h}d hold, 10 bps/side", best_ev, h, 10)
        run(f"Best rule, {h}d hold, hedged, 5 bps/side", best_ev, h, 5, hedge=True, curve=(h == 5))
    res["portfolio"] = port
    res["curves"] = {k: weekly(v) for k, v in curves.items()}
    res["exposure_best"] = float(best_ev["date"].nunique() / len(dates))

    # Latest signals (most recent session) for a look at what the rule flags now.
    last = ev["date"].max()
    recent = ev[ev["date"] >= last - pd.Timedelta(days=7)].copy()
    recent["best_rule"] = rule_mask(recent, best["parts"])
    res["recent"] = recent.sort_values(["date", "ret"])[
        ["date", "ticker", "sector", "close", "ret", "ret5_prior", "gap", "sector_ret", "best_rule"]
    ].assign(date=lambda d: d["date"].dt.strftime("%Y-%m-%d")).to_dict("records")

    keep = ["date", "ticker", "sector", "close", "ret", "gap", "volume", "rvol", "sector_ret", "spy_ret",
            "vix", "trend", "close_loc", "ret5_prior", "next_gap"] + [f"r{h}" for h in HOLDS] + [f"x{h}" for h in HOLDS]
    ev[keep].to_csv(OUT / "events.csv.gz", index=False, float_format="%.5f")
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=float))

    # ---- console report
    pct = lambda v: f"{v*100:+.3f}%"
    o = res["overall"]
    print(f"signals: {o['n']:,} on {o['days']:,} days (no point-in-time filter: {res['no_pit']['n']:,})")
    for h in HOLDS:
        a, b, c = o[f"h{h}"], res["baseline"][f"h{h}"], res["no_pit"][f"h{h}"]
        print(f"  {h}d: raw {pct(a['mean'])} vs baseline {pct(b['mean'])} | per-day basket {pct(a['daily_mean'])} | "
              f"EDGE vs same-day universe {pct(a['edge'])} t={a['t']:.2f} | win {a['win']*100:.1f}% | no-PIT edge {pct(c['edge'])}")
    print(f"  next-open gap mean {pct(o['next_gap_mean'])}, share gapping -2% or worse {o['next_gap_bad']*100:.1f}%")
    for col, title in SPLITS.items():
        print(f"\n{title}  (3d edge vs universe: all | 2005-15 | 2016-26)")
        bp = res["splits"][col]["by_period"]
        lookup = {p: {r["bucket"]: r for r in rows} for p, rows in bp.items()}
        for r in res["splits"][col]["rows"]:
            parts = []
            for p in sorted(lookup):
                q = lookup[p].get(r["bucket"])
                parts.append(f"{pct(q['h3']['edge'])} t={q['h3']['t']:5.2f}" if q else "   n/a   ")
            print(f"  {r['bucket']:<42} n={r['n']:>7,} | {pct(r['h3']['edge'])} t={r['h3']['t']:5.2f} | " + " | ".join(parts))
    print("\nRule search (3d edge vs universe), top 15 by in-sample t:")
    for r in rules[:15]:
        print(f"  {r['rule']:<62} IS {pct(r['edge_is'])} t={r['t_is']:5.2f} n={r['n_is']:>6,} | "
              f"OOS {pct(r['edge_oos'])} t={r['t_oos']:5.2f} n={r['n_oos']:>6,}")
    print(f"\nBEST RULE (chosen in-sample): {best['rule']}")
    print("\nPortfolio                                     full: CAGR  Sharpe  maxDD | 2016+: CAGR  Sharpe  maxDD")
    for k, v in port.items():
        f_, s_ = v["full"], v["oos"]
        print(f"  {k:<44} {f_['cagr']*100:6.2f}% {f_['sharpe']:5.2f} {f_['max_dd']*100:6.1f}% | "
              f"{s_['cagr']*100:6.2f}% {s_['sharpe']:5.2f} {s_['max_dd']*100:6.1f}%")


if __name__ == "__main__":
    main()
