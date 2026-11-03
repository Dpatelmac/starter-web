"""Turn one or more backtest results files into compact chart data and inject them into the offline HTML template.

usage: build_report.py <template.html> <out.html> <results.json> "<window label>" "<period text>" [<results.json> "<label>" "<period>" ...]
Each results file becomes one selectable window in the report.
"""
import json, sys, datetime as dt
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
tpl_path, out_path, *rest = sys.argv[1:]
assert rest and len(rest) % 3 == 0, __doc__


def dur_min(bar):
    if bar == "1D":
        return 390
    if bar.endswith("H"):
        return int(bar[:-1]) * 60
    return int(bar[:-1])


def build_window(R, label, period):
    fetch = max(dt.datetime.fromtimestamp(row[0], NY) for r in R for row in r["series"])  # last (live) bar
    days = sorted({dt.datetime.fromtimestamp(row[0], NY).date() for r in R for row in r["series"]})
    day_idx = {d: i for i, d in enumerate(days)}
    long_window = len(days) > 260
    tfmt = "%b %d '%y" if long_window else "%b %d %H:%M"

    def xpos(t):
        """Trading-time axis: each session is 390 minutes, nights and weekends collapsed."""
        t = min(t, fetch)
        m = (t.hour * 60 + t.minute + t.second / 60) - (9 * 60 + 30)
        return round(day_idx[t.date()] * 390 + max(0, min(390, m)), 1)

    win = {"label": label, "period": period, "days": [d.strftime("%Y-%m-%d") for d in days],
           "fetched": fetch.strftime("%b %d, %Y %H:%M ET"), "capital": 10000, "tfs": []}
    for r in R:
        tf, bar = r["tf"], r.get("bar", r["tf"])
        intraday_fmt = "%b %d '%y %H:%M" if long_window and bar != "1D" else tfmt
        xo, xc = [], []
        for row in r["series"]:
            t = dt.datetime.fromtimestamp(row[0], NY)
            aligned = t.second == 0 and (t.minute in (0, 30) or not (bar == "1D" or bar.endswith("H"))) and not (bar == "1D" and t.minute != 30)
            end = t + dt.timedelta(minutes=dur_min(bar)) if aligned else t
            end = min(end, t.replace(hour=16, minute=0, second=0))
            xo.append(xpos(t)); xc.append(xpos(end))
        for i in range(1, len(xc)):                     # keep the axis monotonic
            xc[i] = max(xc[i], xc[i - 1])
        ts = [row[0] for row in r["series"]]
        pos = {t: i for i, t in enumerate(ts)}
        trades = []
        for tr in r["trades"]:
            et = dt.datetime.fromisoformat(tr["entry_t"]); xt = dt.datetime.fromisoformat(tr["exit_t"])
            ie, ix = pos[int(et.timestamp())], pos[int(xt.timestamp())]
            trades.append(dict(et=et.strftime(intraday_fmt), xt=xt.strftime(intraday_fmt),
                               ep=round(tr["entry_px"], 2), xp=round(tr["exit_px"], 2), q=tr["qty"],
                               pnl=round(tr["pnl"], 2), pct=round(tr["pct"], 2), why=tr["reason"],
                               ex=xo[ie], xx=round((xo[ix] + xc[ix]) / 2, 1), ie=ie, ix=ix,
                               runup=round(tr["runup"], 2), dd=round(tr["dd"], 2), open=False))
        op = r["open"]
        if op:
            et = dt.datetime.fromisoformat(op["entry_t"]); ie = pos[int(et.timestamp())]
            trades.append(dict(et=et.strftime(intraday_fmt), xt="open", ep=round(op["entry_px"], 2),
                               xp=round(op["mark"], 2), q=op["qty"], pnl=round(op["pnl"], 2),
                               pct=round(op["pnl"] / (op["entry_px"] * op["qty"]) * 100, 2),
                               why="Still open · " + op["phase"] + f" stop ${op['stop']:.2f}",
                               ex=xo[ie], xx=None, ie=ie, ix=None, runup=None, dd=None, open=True))
        stats = {k: r[k] for k in ("net", "net_pct", "closed", "closed_trades", "wins", "losses", "winrate", "gp",
                                   "gl", "pf", "avg", "avg_win", "avg_loss", "maxdd", "maxdd_pct", "final_eq",
                                   "bh_final", "bh_pct", "first_px", "last_px", "bh_qty")}
        stats["open_pnl"] = op["pnl"] if op else 0
        stats["first"] = r["first"][:16]; stats["last"] = r["last"][:16]
        prm = r.get("params") or dict(dip=60.0, wide=95.0, tgt=60.0, tight=10.0, pct=False, reb=0.5)
        lv = r["levels"]
        dip = [(v[6] if len(v) > 6 else (round(v[1] - prm["dip"], 2) if v[1] is not None else None)) if v[0] == 0 else None for v in lv]
        reb = [round(v[2] * (1 + prm["reb"] / 100), 2) if v[0] == 1 and v[2] is not None else None for v in lv]
        win["tfs"].append(dict(tf=tf, bar=bar, mode=r.get("mode", "$"), params=prm, xo=xo, xc=xc, t=ts,
                               o=[s[1] for s in r["series"]], h=[s[2] for s in r["series"]],
                               l=[s[3] for s in r["series"]], c=[s[4] for s in r["series"]],
                               eq=[s[5] for s in r["series"]], bh=[s[6] for s in r["series"]],
                               st=[v[0] for v in lv], dip=dip, reb=reb,
                               stop=[v[3] for v in lv], buy=[v[4] for v in lv], tgt=[v[5] for v in lv],
                               trades=trades, stats=stats))
    return win


windows = [build_window(json.load(open(rest[i])), rest[i + 1], rest[i + 2]) for i in range(0, len(rest), 3)]
html = open(tpl_path).read().replace("/*__DATA__*/null", json.dumps(windows, separators=(",", ":")))
open(out_path, "w").write(html)
print("wrote", out_path, len(html) // 1024, "KB")
