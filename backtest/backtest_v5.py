"""V5: the V4 idea (trend rule + real stop-loss order + re-entry rule) on 4H bars, searched for a LOWER drawdown than V4
while keeping profit above buy & hold.

- 4H bars are built from 1H bars on TradingView's session split for US stocks (09:30-13:30, 13:30-16:00).
- Broker rules and drawdown measurement are V4's (backtest_v4.run): signals at the bar close, market orders at the next
  bar's open, stop orders fill at the stop or at the open on a gap, 0.1% commission, 100% of equity, long/flat.
- Trend rules (4H bars):  sma f/s/band  (V3/V4 rule) · supertrend n/k (direction of ta.supertrend) ·
                          donchian in/out (close above prior in-bar high → up, close below prior out-bar low → down)
- Stops: none · trail p% · atr k (k × ATR14 on 4H below the highest high) · atrcap k/p (ATR stop, never more than p%)
- Re-entry after a stop-out: fresh (wait for the trend to turn down and up) · hiN (close above the prior N-bar closing high)
- 1D baseline: V4 on daily bars over the same window.

usage:
  backtest_v5.py search <data_dir> <SYMBOL> <start> <end|-> <out.json> [bar 4H|1D] [grid base|two]
  backtest_v5.py report <data_dir> <SYMBOL> <start> <end|-> <out.json> "<key>|<bar>|<trend>|<stop>|<reentry>|<name>;..."
      bar = 4H | 1D    trend = sma:8,50,1.0 | supertrend:14,4.0 | donchian:40,20    stop = none | trail:12 | atr:5.0 | atrcap:6.0/25
"""
import json, sys, os, itertools, importlib.util, datetime as dt

here = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("v4", os.path.join(here, "backtest_v4.py"))
v4 = importlib.util.module_from_spec(_spec); _argv = sys.argv; sys.argv = ["v4"]; _spec.loader.exec_module(v4); sys.argv = _argv
v3 = v4.v3
NY = v3.NY


def load_1h(data_dir, sym):
    r = json.load(open(f"{data_dir}/{sym}_1h.json"))["chart"]["result"][0]
    q = r["indicators"]["quote"][0]; out = []
    for i, t in enumerate(r["timestamp"]):
        o, h, l, c = q["open"][i], q["high"][i], q["low"][i], q["close"][i]
        if None in (o, h, l, c):
            continue
        out.append(dict(t=dt.datetime.fromtimestamp(t, NY), o=o, h=h, l=l, c=c))
    return out


def to_nh(bars1h, n):
    """TradingView session-aligned N-hour bars for US stocks, anchored at 09:30 (same as backtest.py)."""
    out = {}
    for b in bars1h:
        seg = max(0, (b["t"].hour * 60 + b["t"].minute) - 570) // (60 * n)
        k = (b["t"].date(), seg)
        if k not in out:
            out[k] = dict(b)
        else:
            a = out[k]; a["h"] = max(a["h"], b["h"]); a["l"] = min(a["l"], b["l"]); a["c"] = b["c"]
    return list(out.values())


def bars_for(data_dir, sym, bar):
    return v3.load(data_dir, sym) if bar == "1D" else to_nh(load_1h(data_dir, sym), int(bar[:-1]))


# ───────────────────────────── trend rules → (trend[], lines) ─────────────────────────────
def trend_of(b, spec):
    kind, ps = spec.split(":")
    p = [float(x) if "." in x else int(x) for x in ps.split(",")]
    if kind == "sma":
        tr, f, s = v4.trend_band(b, *p)
        return tr, [(f"SMA {p[0]}", f), (f"SMA {p[1]}", s)]
    if kind == "supertrend":
        st, d = v3.supertrend(b, p[1], p[0])
        return [x == -1 for x in d], [(f"Supertrend {p[0]}/{p[1]:g}", st)]
    if kind == "donchian":
        want, lines = v3.f_donchian(b, p[0], p[1])
        return want, lines
    raise ValueError(spec)


TRENDS = ([f"sma:{f},{s},{bd}" for f in (8, 12, 16, 20, 30) for s in (40, 60, 80, 100, 120, 150) for bd in (0.0, 1.0, 2.0) if f < s]
          + [f"supertrend:{n},{k}" for n in (10, 14, 20, 30) for k in (2.0, 3.0, 4.0, 5.0, 6.0)]
          + [f"donchian:{i},{o}" for i in (20, 40, 60, 100) for o in (10, 20, 40) if o <= i])
STOPS = (["none"] + [f"trail:{p}" for p in (8.0, 10.0, 12.0, 15.0, 20.0)] + [f"atr:{k}" for k in (3.0, 4.0, 5.0, 6.0, 8.0)]
         + [f"atrcap:{k}/{p}" for k, p in ((5.0, 20.0), (6.0, 20.0), (6.0, 25.0), (8.0, 25.0))])
REENTRY = ["fresh", "hi20", "hi40"]

# two-stage stop grid ("two"): wide k1 x ATR until the best gain reaches g%, then tighter k2 x ATR
TRENDS_1D = [f"sma:{f},{s},{bd}" for f in (5, 8, 10, 15, 20) for s in (30, 40, 45, 50, 60) for bd in (0.0, 1.0, 2.0) if f < s]
STOPS_TWO = (["atr:5.0"] + [f"atr2:{k1}/{k2}/{g}" for k1 in (4.0, 5.0, 6.0) for k2 in (1.5, 2.0, 2.5, 3.0, 3.5, 4.0) if k2 < k1
                            for g in (10.0, 15.0, 20.0, 30.0, 50.0)])
GRIDS = {("4H", "base"): (TRENDS, STOPS, REENTRY), ("4H", "two"): ([t for t in TRENDS if t.startswith("sma")], STOPS_TWO, ["hi20", "hi40"]),
         ("1D", "base"): (TRENDS_1D, STOPS, ["fresh", "hi10", "hi20"]), ("1D", "two"): (TRENDS_1D, STOPS_TWO, ["hi10", "hi20"])}


def one(b, a14, trend, stop, re_, start, end):
    sk, sv = v4.parse_stop(stop)
    trend = [t and a14[i] is not None for i, t in enumerate(trend)]     # no entries before ATR(14) exists
    return v4.run(b, trend, sk, sv, re_, start, end, a14)


if __name__ == "__main__":
    mode, data_dir, sym = sys.argv[1:4]
    start, end = v3.window(sys.argv[4:6]); out_path = sys.argv[6]
    if mode == "search":
        bar = sys.argv[7] if len(sys.argv) > 7 else "4H"; grid = sys.argv[8] if len(sys.argv) > 8 else "base"
        G_TR, G_ST, G_RE = GRIDS[(bar, grid)]
        b = bars_for(data_dir, sym, bar); a14 = v3.atr(b, 14)
        rows = []
        for ts in G_TR:
            tr = trend_of(b, ts)[0]
            for stop, re_ in itertools.product(G_ST, G_RE):
                if stop == "none" and re_ != "fresh":
                    continue
                s = v3.stats(one(b, a14, tr, stop, re_, start, end))
                rows.append(dict(trend=ts, stop=stop, re=re_, final=round(s["final_eq"], 2), maxdd=round(s["maxdd_pct"], 2),
                                 trades=s["closed_trades"], exposure=round(s["exposure"], 1), bh=s["bh_final"], bh_dd=s["bh_dd"]))
        json.dump(dict(symbol=sym, bar=bar, grid=grid, start=sys.argv[4], end=sys.argv[5], rows=rows), open(out_path, "w"))
        bh, bdd = rows[0]["bh"], rows[0]["bh_dd"]
        good = [r for r in rows if r["final"] > bh and r["maxdd"] < bdd]
        print(f"{sym} {bar}/{grid} {sys.argv[4]}→{sys.argv[5]}  B&H ${bh:,.0f} dd {bdd:.1f}%  combos {len(rows)}  beat on both {len(good)}")
        for r in sorted(good, key=lambda r: r["maxdd"])[:12]:
            print(f"  {r['trend']:<22}{r['stop']:<14}{r['re']:<6} ${r['final']:>10,.0f}  dd {r['maxdd']:5.1f}%  trades {r['trades']:3d}")
    else:
        out, cache = [], {}
        for spec in sys.argv[7].split(";"):
            key, bar, ts, stop, re_, name = spec.split("|")
            if bar not in cache:
                bb = bars_for(data_dir, sym, bar); cache[bar] = (bb, v3.atr(bb, 14))
            b, a14 = cache[bar]
            tr, lines = trend_of(b, ts)
            res = one(b, a14, tr, stop, re_, start, end)
            st = v3.stats(res)
            ser = lambda d: str(d)
            sel = lambda arr: [None if arr[i] is None else round(arr[i], 2) for i in res["idx"]]
            L = [dict(name=n, values=sel(v)) for n, v in lines]
            if stop != "none":
                L.append(dict(name=f"Stop ({v4.fmt_stop(*v4.parse_stop(stop))})", values=res["stop_line"]))
            out.append(dict(tf=key, bar=bar, mode="%", name=name, kind="trend", symbol=sym, subject=v3.SUBJECT.get(sym, sym),
                            params=dict(dip=0, wide=0, tgt=0, tight=0, pct=True, reb=0, trend=False),
                            series=res["series"], levels=res["levels"], lines=L,
                            trades=[{k: (ser(v) if isinstance(v, dt.datetime) else v) for k, v in t.items()} for t in res["trades"]],
                            open=({k: (ser(v) if isinstance(v, dt.datetime) else v) for k, v in res["open"].items()} if res["open"] else None),
                            first=str(res["first"]["t"]), last=str(res["last"]["t"]), **st))
            print(f"{key:<10} {bar:<3} ${st['final_eq']:>11,.2f} ({st['net_pct']:+.0f}%)  dd {st['maxdd_pct']:.1f}%  trades {st['closed_trades']}  "
                  f"win {st['winrate'] or 0:.0f}%  in-mkt {st['exposure']:.0f}%   B&H ${st['bh_final']:,.0f} dd {st['bh_dd']:.1f}%")
        json.dump(out, open(out_path, "w"), default=str, separators=(",", ":"))
