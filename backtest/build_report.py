"""Turn results.json into compact chart data and inject it into the offline HTML template."""
import json, sys, datetime as dt
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
# usage: build_report.py <results.json> <template.html> <out.html> "<period label>"
res_path, tpl_path, out_path, period = sys.argv[1:5]
R = json.load(open(res_path))
FETCH = max(dt.datetime.fromtimestamp(row[0], NY) for r in R for row in r["series"])  # time of the last (live) bar


def dur_min(tf):
    if tf == "1D":
        return 390
    if tf.endswith("H"):
        return int(tf[:-1]) * 60
    return int(tf[:-1])

days = sorted({dt.datetime.fromtimestamp(row[0], NY).date() for r in R for row in r["series"]})
day_idx = {d: i for i, d in enumerate(days)}


def xpos(t):
    """Trading-time axis: each session is 390 minutes, nights and weekends collapsed."""
    t = min(t, FETCH)
    m = (t.hour * 60 + t.minute + t.second / 60) - (9 * 60 + 30)
    return round(day_idx[t.date()] * 390 + max(0, min(390, m)), 2)


out = {"days": [d.strftime("%Y-%m-%d") for d in days], "fetched": FETCH.strftime("%b %d, %Y %H:%M ET"),
       "capital": 10000, "period": period, "tfs": []}
for r in R:
    tf = r["tf"]
    xo, xc = [], []
    for row in r["series"]:
        t = dt.datetime.fromtimestamp(row[0], NY)
        aligned = t.second == 0 and (t.minute in (0, 30) or not (tf == "1D" or tf.endswith("H"))) and not (tf == "1D" and t.minute != 30)
        dur = dur_min(tf)
        end = t + dt.timedelta(minutes=dur) if aligned else t
        end = min(end, t.replace(hour=16, minute=0, second=0))
        xo.append(xpos(t)); xc.append(xpos(end))
    for i in range(1, len(xc)):                     # keep the axis monotonic
        xc[i] = max(xc[i], xc[i - 1])
    ts = [row[0] for row in r["series"]]
    trades = []
    for tr in r["trades"]:
        et = dt.datetime.fromisoformat(tr["entry_t"]); xt = dt.datetime.fromisoformat(tr["exit_t"])
        ie, ix = ts.index(int(et.timestamp())), ts.index(int(xt.timestamp()))
        trades.append(dict(et=et.strftime("%b %d %H:%M"), xt=xt.strftime("%b %d %H:%M"),
                           ep=round(tr["entry_px"], 2), xp=round(tr["exit_px"], 2), q=tr["qty"],
                           pnl=round(tr["pnl"], 2), pct=round(tr["pct"], 2), why=tr["reason"],
                           ex=xo[ie], xx=round((xo[ix] + xc[ix]) / 2, 2), ie=ie, ix=ix,
                           runup=round(tr["runup"], 2), dd=round(tr["dd"], 2), open=False))
    op = r["open"]
    if op:
        et = dt.datetime.fromisoformat(op["entry_t"]); ie = ts.index(int(et.timestamp()))
        trades.append(dict(et=et.strftime("%b %d %H:%M"), xt="open", ep=round(op["entry_px"], 2),
                           xp=round(op["mark"], 2), q=op["qty"], pnl=round(op["pnl"], 2),
                           pct=round(op["pnl"] / (op["entry_px"] * op["qty"]) * 100, 2),
                           why="Still open · " + op["phase"] + f" stop ${op['stop']:.2f}",
                           ex=xo[ie], xx=None, ie=ie, ix=None, runup=None, dd=None, open=True))
    stats = {k: r[k] for k in ("net", "net_pct", "closed", "closed_trades", "wins", "losses", "winrate", "gp",
                               "gl", "pf", "avg", "avg_win", "avg_loss", "maxdd", "maxdd_pct", "final_eq",
                               "bh_final", "bh_pct", "first_px", "last_px", "bh_qty")}
    stats["open_pnl"] = op["pnl"] if op else 0
    stats["first"] = r["first"][:16]; stats["last"] = r["last"][:16]
    lv = r["levels"]
    out["tfs"].append(dict(tf=tf, xo=xo, xc=xc, t=ts,
                           o=[s[1] for s in r["series"]], h=[s[2] for s in r["series"]],
                           l=[s[3] for s in r["series"]], c=[s[4] for s in r["series"]],
                           eq=[s[5] for s in r["series"]], bh=[s[6] for s in r["series"]],
                           st=[v[0] for v in lv], tH=[v[1] for v in lv], tL=[v[2] for v in lv],
                           stop=[v[3] for v in lv], buy=[v[4] for v in lv], tgt=[v[5] for v in lv],
                           trades=trades, stats=stats))

html = open(tpl_path).read().replace("/*__DATA__*/null", json.dumps(out, separators=(",", ":")))
open(out_path, "w").write(html)
print("wrote", out_path, len(html) // 1024, "KB")
