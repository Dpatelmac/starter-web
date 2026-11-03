"""V3: search long/flat trend-following strategies on the daily chart that try to beat buy & hold.

Same broker rules as V1/V2 (TradingView-style): signals at the bar close, market orders fill at the next bar's
open, qty = floor(equity / close at the signal bar), 0.1% commission per side, no slippage, 100% of equity.
Indicators replicate TradingView's built-ins (ta.sma, ta.ema, ta.rma, ta.atr, ta.supertrend, ta.highest/lowest).

usage:
  backtest_v3.py search  <data_dir> <SYMBOL> <start> <end|-> <out.json>
  backtest_v3.py report  <data_dir> <SYMBOL> <start> <end|-> <out.json> "<key>|<family>|<p1>,<p2>,..|<name>;..."
"""
import json, math, sys, itertools, datetime as dt
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
SUBJECT = {"LITE": "Lumentum (NASDAQ: LITE)", "COHR": "Coherent (NYSE: COHR)", "AAOI": "Applied Optoelectronics (NASDAQ: AAOI)",
           "CIEN": "Ciena (NYSE: CIEN)", "NVDA": "NVIDIA (NASDAQ: NVDA)"}
CAP0, COMM = 10000.0, 0.001


# ───────────────────────────── data ─────────────────────────────
def load(data_dir, sym):
    r = json.load(open(f"{data_dir}/{sym}_1d.json"))["chart"]["result"][0]
    q = r["indicators"]["quote"][0]
    out = []
    for i, t in enumerate(r["timestamp"]):
        o, h, l, c = q["open"][i], q["high"][i], q["low"][i], q["close"][i]
        if None in (o, h, l, c):
            continue
        out.append(dict(t=dt.datetime.fromtimestamp(t, NY), o=o, h=h, l=l, c=c))
    return out


# ──────────────────── TradingView-equivalent indicators ────────────────────
def sma(x, n):
    out, s = [None] * len(x), 0.0
    for i, v in enumerate(x):
        s += v
        if i >= n:
            s -= x[i - n]
        if i >= n - 1:
            out[i] = s / n
    return out


def _seeded(x, n, alpha):                       # ta.ema / ta.rma: seeded with the SMA of the first n values
    out, prev = [None] * len(x), None
    for i, v in enumerate(x):
        if prev is None:
            if i >= n - 1:
                prev = sum(x[i - n + 1:i + 1]) / n
                out[i] = prev
        else:
            prev = alpha * v + (1 - alpha) * prev
            out[i] = prev
    return out


def ema(x, n): return _seeded(x, n, 2 / (n + 1))
def rma(x, n): return _seeded(x, n, 1 / n)


def atr(b, n):
    tr = [b[0]["h"] - b[0]["l"]] + [max(b[i]["h"] - b[i]["l"], abs(b[i]["h"] - b[i - 1]["c"]), abs(b[i]["l"] - b[i - 1]["c"]))
                                    for i in range(1, len(b))]
    return rma(tr, n)


def highest(x, n):                               # ta.highest(x, n) including the current bar
    return [max(x[i - n + 1:i + 1]) if i >= n - 1 else None for i in range(len(x))]


def lowest(x, n):
    return [min(x[i - n + 1:i + 1]) if i >= n - 1 else None for i in range(len(x))]


def supertrend(b, factor, n):
    """Exact port of TradingView's ta.supertrend(factor, atrPeriod) -> (line, direction); direction -1 = up."""
    a = atr(b, n)
    st, dirn = [None] * len(b), [None] * len(b)
    lo_p = up_p = st_p = None
    for i in range(len(b)):
        src = (b[i]["h"] + b[i]["l"]) / 2
        if a[i] is None:
            continue
        ub, lb = src + factor * a[i], src - factor * a[i]
        plb, pub = (lo_p or 0.0), (up_p or 0.0)
        cprev = b[i - 1]["c"]
        lb = lb if (lb > plb or cprev < plb) else plb
        ub = ub if (ub < pub or cprev > pub) else pub
        if i == 0 or a[i - 1] is None:
            d = 1
        elif st_p == pub:
            d = -1 if b[i]["c"] > ub else 1
        else:
            d = 1 if b[i]["c"] < lb else -1
        s = lb if d == -1 else ub
        st[i], dirn[i] = s, d
        lo_p, up_p, st_p = lb, ub, s
    return st, dirn


# ───────────────────────────── strategy families ─────────────────────────────
# Each returns (want, lines): want[i] = desired position after the close of bar i (True = long),
# lines = [(name, values)] to draw on the price chart.
def f_ma_cross(b, kind, fast, slow):
    c = [x["c"] for x in b]
    m = ema if kind == "ema" else sma
    f, s = m(c, fast), m(c, slow)
    want = [f[i] is not None and s[i] is not None and f[i] > s[i] for i in range(len(b))]
    return want, [(f"{kind.upper()} {fast}", f), (f"{kind.upper()} {slow}", s)]


def f_above_ma(b, kind, n):
    c = [x["c"] for x in b]
    m = (ema if kind == "ema" else sma)(c, n)
    return [m[i] is not None and c[i] > m[i] for i in range(len(b))], [(f"{kind.upper()} {n}", m)]


def f_donchian(b, n_in, n_out):
    hi = highest([x["h"] for x in b], n_in); lo = lowest([x["l"] for x in b], n_out)
    want, pos, up, dn = [], False, [None] * len(b), [None] * len(b)
    for i in range(len(b)):
        h1 = hi[i - 1] if i > 0 else None; l1 = lo[i - 1] if i > 0 else None
        up[i], dn[i] = h1, l1
        if not pos and h1 is not None and b[i]["c"] > h1:
            pos = True
        elif pos and l1 is not None and b[i]["c"] < l1:
            pos = False
        want.append(pos)
    return want, [(f"{n_in}-day high", up), (f"{n_out}-day low", dn)]


def f_supertrend(b, n, factor):
    st, d = supertrend(b, factor, n)
    return [d[i] == -1 for i in range(len(b))], [(f"Supertrend {n}/{factor}", st)]


def f_roc(b, n):
    c = [x["c"] for x in b]
    return [i >= n and c[i] > c[i - n] for i in range(len(b))], []


def f_macd(b, fast, slow, sig):
    c = [x["c"] for x in b]
    ef, es = ema(c, fast), ema(c, slow)
    macd = [None if ef[i] is None or es[i] is None else ef[i] - es[i] for i in range(len(b))]
    first = next(i for i, v in enumerate(macd) if v is not None)
    sg = [None] * first + ema(macd[first:], sig)
    return [macd[i] is not None and sg[i] is not None and macd[i] > sg[i] for i in range(len(b))], []


def f_chandelier(b, n_in, atr_n, k):
    """Enter on a close above the prior n_in-day closing high; exit on a close below (highest high since entry - k*ATR)."""
    c = [x["c"] for x in b]; hc = highest(c, n_in); a = atr(b, atr_n)
    want, pos, hh, line = [], False, None, [None] * len(b)
    for i in range(len(b)):
        if not pos:
            if i > 0 and hc[i - 1] is not None and a[i] is not None and c[i] > hc[i - 1]:
                pos, hh = True, b[i]["h"]
        else:
            hh = max(hh, b[i]["h"])
            if c[i] < hh - k * a[i]:
                pos = False
        line[i] = hh - k * a[i] if pos and a[i] is not None else None
        want.append(pos)
    return want, [(f"Chandelier stop {k}×ATR{atr_n}", line)]


def f_sma_band(b, fast, slow, band):
    """SMA cross with a hysteresis band: enter when fast > slow*(1+band%), exit when fast < slow*(1-band%)."""
    c = [x["c"] for x in b]; f, s = sma(c, fast), sma(c, slow)
    want, pos = [], False
    for i in range(len(b)):
        if f[i] is not None and s[i] is not None:
            if not pos and f[i] > s[i] * (1 + band / 100):
                pos = True
            elif pos and f[i] < s[i] * (1 - band / 100):
                pos = False
        want.append(pos)
    return want, [(f"SMA {fast}", f), (f"SMA {slow}", s)]


def f_dd_trail(b, dd_pct, re_n):
    """Long by default; exit on a close dd_pct% below the highest close since entry; re-enter on a close above EMA(re_n)."""
    c = [x["c"] for x in b]; e = ema(c, re_n)
    want, pos, hc, line = [], False, None, [None] * len(b)
    for i in range(len(b)):
        if not pos:
            if e[i] is not None and c[i] > e[i]:
                pos, hc = True, c[i]
        else:
            hc = max(hc, c[i])
            if c[i] < hc * (1 - dd_pct / 100):
                pos = False
        line[i] = hc * (1 - dd_pct / 100) if pos else None
        want.append(pos)
    return want, [(f"{dd_pct}% trailing stop (close)", line), (f"EMA {re_n} (re-entry)", e)]


FAMILIES = {
    "ema_cross":  (lambda b, f, s: f_ma_cross(b, "ema", f, s),
                   [(f, s) for f in (5, 10, 15, 20, 30, 50) for s in (20, 30, 50, 75, 100, 150, 200) if f < s]),
    "sma_cross":  (lambda b, f, s: f_ma_cross(b, "sma", f, s),
                   [(f, s) for f in (5, 8, 10, 12, 15, 18, 20, 25, 30, 50) for s in (20, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 100, 150, 200) if f < s]),
    "above_ema":  (lambda b, n: f_above_ma(b, "ema", n), [(n,) for n in (10, 15, 20, 30, 40, 50, 75, 100, 150, 200)]),
    "above_sma":  (lambda b, n: f_above_ma(b, "sma", n), [(n,) for n in (10, 15, 20, 30, 40, 50, 75, 100, 150, 200)]),
    "donchian":   (f_donchian, [(i, o) for i in (10, 20, 30, 40, 55, 75, 100) for o in (5, 10, 15, 20, 30, 50) if o <= i]),
    "supertrend": (f_supertrend, [(n, k) for n in (7, 10, 14, 20, 30) for k in (1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0)]),
    "roc":        (f_roc, [(n,) for n in (10, 20, 30, 50, 75, 100, 126, 150, 200)]),
    "macd":       (f_macd, [(f, s, g) for f, s in ((8, 21), (12, 26), (19, 39)) for g in (5, 9, 12)]),
    "sma_band":   (f_sma_band, [(f, sl, bd) for f in (8, 10, 15, 20) for sl in (40, 45, 50, 55, 60) for bd in (0.5, 1.0, 2.0, 3.0)]),
    "dd_trail":   (f_dd_trail, [(d, n) for d in (8, 10, 12, 15, 20, 25, 30) for n in (5, 10, 20, 30, 50)]),
    "chandelier": (f_chandelier, [(n, a, k) for n in (10, 20, 50) for a in (14, 22) for k in (2.0, 3.0, 4.0, 5.0)]),
}


# ───────────────────────────── broker simulation ─────────────────────────────
def simulate(b, want, start, end):
    idx = [i for i, x in enumerate(b) if x["t"] >= start and (end is None or x["t"] <= end)]
    cash, qty, pend, pend_qty = CAP0, 0, None, 0
    trades, entry, series, levels = [], None, [], []
    peak, maxdd, maxdd_pct, in_mkt = CAP0, 0.0, 0.0, 0
    for n, i in enumerate(idx):
        x = b[i]
        if pend == "buy":
            qty = pend_qty; fee = qty * x["o"] * COMM; cash -= qty * x["o"] + fee
            entry = dict(t=x["t"], px=x["o"], qty=qty, fee=fee, hi=x["h"], lo=x["l"])
        elif pend == "sell" and qty:
            fee = qty * x["o"] * COMM; cash += qty * x["o"] - fee
            pnl = (x["o"] - entry["px"]) * qty - entry["fee"] - fee
            trades.append(dict(entry_t=entry["t"], entry_px=entry["px"], exit_t=x["t"], exit_px=x["o"], qty=qty, pnl=pnl,
                               pct=pnl / (entry["px"] * qty) * 100, reason=pend_why,
                               runup=(entry["hi"] - entry["px"]) * qty, dd=(entry["lo"] - entry["px"]) * qty))
            qty, entry = 0, None
        pend = None
        if qty:
            entry["hi"] = max(entry["hi"], x["h"]); entry["lo"] = min(entry["lo"], x["l"]); in_mkt += 1
        eq_c, eq_l = cash + qty * x["c"], cash + qty * x["l"]
        peak = max(peak, cash + qty * x["h"]) if qty else max(peak, eq_c)
        maxdd = max(maxdd, peak - min(eq_l, eq_c)); maxdd_pct = max(maxdd_pct, (peak - min(eq_l, eq_c)) / peak * 100)
        series.append([int(x["t"].timestamp()), round(x["o"], 2), round(x["h"], 2), round(x["l"], 2), round(x["c"], 2), round(eq_c, 2)])
        last = n == len(idx) - 1
        if not last:                                   # decide at this close, fill at the next open
            if want[i] and not qty:
                pend, pend_qty = "buy", math.floor(cash / x["c"])
            elif not want[i] and qty:
                pend, pend_why = "sell", "trend exit"
        st = 2 if (qty or pend == "buy") and pend != "sell" else 0
        levels.append([st, None, None, None, round(entry["px"], 2) if entry else None, None, None, None])
    first, lastb = b[idx[0]], b[idx[-1]]
    open_t = None
    if qty:
        open_t = dict(entry_t=entry["t"], entry_px=entry["px"], qty=qty, mark=lastb["c"],
                      pnl=(lastb["c"] - entry["px"]) * qty - entry["fee"], stop=0.0, phase="trend still up")
    final = cash + qty * lastb["c"]
    bh_qty = math.floor(CAP0 / first["o"]); bh_cash = CAP0 - bh_qty * first["o"] * (1 + COMM)
    for row in series:
        row.append(round(bh_cash + bh_qty * row[4], 2))
    bh_final = bh_cash + bh_qty * lastb["c"]
    # buy & hold max drawdown (intrabar) for comparison
    pk, bh_dd = CAP0, 0.0
    for i in idx:
        pk = max(pk, bh_cash + bh_qty * b[i]["h"]); bh_dd = max(bh_dd, (pk - (bh_cash + bh_qty * b[i]["l"])) / pk * 100)
    return dict(idx=idx, series=series, levels=levels, trades=trades, open=open_t, final_eq=final, maxdd=maxdd,
                maxdd_pct=maxdd_pct, bh_final=bh_final, bh_qty=bh_qty, bh_dd=bh_dd, first=first, last=lastb,
                exposure=in_mkt / len(idx) * 100)


def stats(res):
    tr = res["trades"]; wins = [t for t in tr if t["pnl"] > 0]; losses = [t for t in tr if t["pnl"] <= 0]
    gp, gl = sum(t["pnl"] for t in wins), -sum(t["pnl"] for t in losses)
    net = res["final_eq"] - CAP0
    yrs = (res["last"]["t"] - res["first"]["t"]).days / 365.25
    return dict(net=net, net_pct=net / CAP0 * 100, closed=sum(t["pnl"] for t in tr), closed_trades=len(tr),
                wins=len(wins), losses=len(losses), winrate=len(wins) / len(tr) * 100 if tr else None,
                gp=gp, gl=gl, pf=gp / gl if gl else None, avg=sum(t["pnl"] for t in tr) / len(tr) if tr else None,
                avg_win=gp / len(wins) if wins else None, avg_loss=-gl / len(losses) if losses else None,
                maxdd=res["maxdd"], maxdd_pct=res["maxdd_pct"], final_eq=res["final_eq"],
                bh_final=res["bh_final"], bh=res["bh_final"] - CAP0, bh_pct=(res["bh_final"] / CAP0 - 1) * 100,
                bh_dd=res["bh_dd"], exposure=res["exposure"],
                cagr=((res["final_eq"] / CAP0) ** (1 / yrs) - 1) * 100 if yrs > 0 else None,
                bh_cagr=((res["bh_final"] / CAP0) ** (1 / yrs) - 1) * 100 if yrs > 0 else None,
                first_px=res["first"]["o"], last_px=res["last"]["c"], bh_qty=res["bh_qty"])


def window(argv):
    start = dt.datetime.fromisoformat(argv[0]).replace(tzinfo=NY)
    end = None if argv[1] == "-" else dt.datetime.fromisoformat(argv[1]).replace(hour=23, tzinfo=NY)
    return start, end


if __name__ == "__main__":
    mode, data_dir, sym = sys.argv[1:4]
    start, end = window(sys.argv[4:6])
    out_path = sys.argv[6]
    b = load(data_dir, sym)
    if mode == "search":
        rows = []
        for fam, (fn, grid) in FAMILIES.items():
            for p in grid:
                want, _ = fn(b, *p)
                s = stats(simulate(b, want, start, end))
                rows.append(dict(family=fam, params=list(p), final=round(s["final_eq"], 2), cagr=s["cagr"],
                                 maxdd=s["maxdd_pct"], trades=s["closed_trades"], winrate=s["winrate"],
                                 exposure=s["exposure"], bh=s["bh_final"], bh_dd=s["bh_dd"]))
        json.dump(dict(symbol=sym, start=sys.argv[4], end=sys.argv[5], rows=rows), open(out_path, "w"))
        bh = rows[0]["bh"]
        print(f"{sym} {sys.argv[4]}→{sys.argv[5]}  B&H ${bh:,.0f} (max dd {rows[0]['bh_dd']:.1f}%)  combos {len(rows)}  beating B&H {sum(r['final'] > bh for r in rows)}")
        for r in sorted(rows, key=lambda r: -r["final"])[:15]:
            print(f"  {r['family']:<11}{str(r['params']):<16} ${r['final']:>11,.0f}  dd {r['maxdd']:5.1f}%  trades {r['trades']:3d}  in-mkt {r['exposure']:5.1f}%")
    else:
        specs = [s.split("|") for s in sys.argv[7].split(";")]
        out = []
        for key, fam, ps, name in specs:
            p = [float(v) if "." in v else int(v) for v in ps.split(",")] if ps else []
            want, lines = FAMILIES[fam][0](b, *p)
            res = simulate(b, want, start, end)
            s = stats(res)
            ser = lambda d: str(d)
            out.append(dict(tf=key, bar="1D", mode="%", name=name, kind="trend", family=fam, fparams=p, symbol=sym,
                            subject=SUBJECT.get(sym, sym),
                            params=dict(dip=0, wide=0, tgt=0, tight=0, pct=True, reb=0, trend=False),
                            series=res["series"], levels=res["levels"],
                            lines=[dict(name=n, values=[None if v is None else round(v, 2) for v in (vals[i] for i in res["idx"])])
                                   for n, vals in lines],
                            trades=[{k: (ser(v) if isinstance(v, dt.datetime) else v) for k, v in t.items()} for t in res["trades"]],
                            open=({k: (ser(v) if isinstance(v, dt.datetime) else v) for k, v in res["open"].items()} if res["open"] else None),
                            first=str(res["first"]["t"]), last=str(res["last"]["t"]), **s))
            print(f"{key:<10} ${s['final_eq']:>11,.2f}  ({s['net_pct']:+.1f}%)  dd {s['maxdd_pct']:.1f}%  trades {s['closed_trades']}  "
                  f"win {s['winrate'] or 0:.0f}%  in-mkt {s['exposure']:.0f}%   B&H ${s['bh_final']:,.2f} dd {s['bh_dd']:.1f}%")
        json.dump(out, open(out_path, "w"), default=str, separators=(",", ":"))
