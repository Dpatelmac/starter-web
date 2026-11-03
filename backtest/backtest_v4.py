"""V4: daily trend entry (SMA cross with a band, as V3) + a real stop-loss order to cut drawdowns.

Goal: beat buy & hold on profit AND have a much lower max drawdown (intrabar, TradingView style).

Rules per bar (TradingView broker emulator, process_orders_on_close = false):
- Market orders are sent at the close and fill at the next bar's open.
- The stop order is placed at the close for the next bar; it fills at the stop, or at the open if the bar opens
  through it. On the entry bar the stop is already active (placed together with the entry).
- Stop types:  trail p%  -> stop = highest high since entry x (1 - p/100)
               atr k     -> stop = highest high since entry - k x ATR(14)
               atrcap k/p -> stop = max(highest high - k x ATR(14), highest high x (1 - p/100))
                            (the ATR stop, but never more than p% below the high)
               none      -> only the trend exit
- Trend exit: sell at the next open when the trend turns down (fast SMA < slow SMA x (1 - band%)).
- Re-entry after a stop-out:  fresh = wait until the trend has turned down and up again
                              hiN   = buy again on a close above the prior N-day closing high while the trend is up
- qty = floor(equity / close at the signal bar), 0.1% commission per side, no slippage, long/flat only.

usage:
  backtest_v4.py search <data_dir> <SYMBOL> <start> <end|-> <out.json>
  backtest_v4.py report <data_dir> <SYMBOL> <start> <end|-> <out.json> "<key>|<fast>,<slow>,<band>|<stop>|<reentry>|<name>;..."
      stop = trail:12 | atr:3 | none      reentry = fresh | hi20 | ...
"""
import json, math, sys, os, itertools, importlib.util, datetime as dt

_spec = importlib.util.spec_from_file_location("v3", os.path.join(os.path.dirname(os.path.abspath(__file__)), "backtest_v3.py"))
v3 = importlib.util.module_from_spec(_spec); _argv = sys.argv; sys.argv = ["v3"]; _spec.loader.exec_module(v3); sys.argv = _argv
NY, CAP0, COMM = v3.NY, v3.CAP0, v3.COMM


def trend_band(b, fast, slow, band):
    c = [x["c"] for x in b]; f, s = v3.sma(c, fast), v3.sma(c, slow)
    tr, pos = [], False
    for i in range(len(b)):
        if f[i] is not None and s[i] is not None:
            if not pos and f[i] > s[i] * (1 + band / 100):
                pos = True
            elif pos and f[i] < s[i] * (1 - band / 100):
                pos = False
        tr.append(pos)
    return tr, f, s


def stop_level(kind, val, hh, atr_now):
    if kind == "trail":
        return hh * (1 - val / 100)
    if kind == "atr":
        return hh - val * atr_now
    if kind == "atrcap":
        k, p = val
        return max(hh - k * atr_now, hh * (1 - p / 100))
    return None


def fmt_stop(kind, val):
    return {"trail": lambda: f"{val:g}% trail", "atr": lambda: f"{val:g}×ATR", "atrcap": lambda: f"{val[0]:g}×ATR, max {val[1]:g}%"}.get(kind, lambda: "none")()


def run(b, trend, stop_kind, stop_val, reentry, start, end, atr14=None):
    c = [x["c"] for x in b]
    hc = None
    if reentry.startswith("hi"):
        hc = v3.highest(c, int(reentry[2:]))
    idx = [i for i, x in enumerate(b) if x["t"] >= start and (end is None or x["t"] <= end)]
    cash, qty, entry = CAP0, 0, None
    pend_buy, pend_qty, pend_sell, stop_next = False, 0, False, None
    hh, blocked = None, False          # blocked: stopped out, waiting for the re-entry condition
    trades, series, levels, stop_line = [], [], [], []
    peak, maxdd, maxdd_pct, in_mkt = CAP0, 0.0, 0.0, 0

    def close_trade(x, px, why):
        nonlocal cash, qty, entry
        fee = qty * px * COMM; cash += qty * px - fee
        pnl = (px - entry["px"]) * qty - entry["fee"] - fee
        trades.append(dict(entry_t=entry["t"], entry_px=entry["px"], exit_t=x["t"], exit_px=px, qty=qty, pnl=pnl,
                           pct=pnl / (entry["px"] * qty) * 100, reason=why,
                           runup=(entry["hi"] - entry["px"]) * qty, dd=(entry["lo"] - entry["px"]) * qty))
        qty, entry = 0, None

    for n, i in enumerate(idx):
        x = b[i]; stopped = False
        # ---- fills at this bar ----
        if pend_sell and qty:
            close_trade(x, x["o"], "trend exit")
        if pend_buy:
            qty = pend_qty; fee = qty * x["o"] * COMM; cash -= qty * x["o"] + fee
            entry = dict(t=x["t"], px=x["o"], qty=qty, fee=fee, hi=x["h"], lo=x["l"])
            hh = x["h"]
        pend_buy = pend_sell = False
        stop_peak = None
        if qty and stop_next is not None and x["l"] <= stop_next:
            entry["hi"] = max(entry["hi"], x["h"]); entry["lo"] = min(entry["lo"], x["l"])
            px = x["o"] if x["o"] <= stop_next else stop_next
            stop_peak = cash + qty * (x["h"] if x["o"] > stop_next else x["o"])   # conservative: the high may come first
            close_trade(x, px, f"stop ({fmt_stop(stop_kind, stop_val)})")
            stopped, blocked = True, True
        elif qty:
            entry["hi"] = max(entry["hi"], x["h"]); entry["lo"] = min(entry["lo"], x["l"]); hh = max(hh, x["h"])
        # ---- equity / drawdown (intrabar) ----
        if qty:
            in_mkt += 1
        eq_c = cash + qty * x["c"]
        eq_l = cash + qty * x["l"]                 # after a stop fill qty = 0, so this is the cash from the fill
        peak = max(peak, cash + qty * x["h"]) if qty else max(peak, eq_c)
        if stop_peak is not None:
            peak = max(peak, stop_peak)
        lowpt = min(eq_l, eq_c)
        maxdd = max(maxdd, peak - lowpt); maxdd_pct = max(maxdd_pct, (peak - lowpt) / peak * 100)
        series.append([int(x["t"].timestamp()), round(x["o"], 2), round(x["h"], 2), round(x["l"], 2), round(x["c"], 2), round(eq_c, 2)])
        # ---- decisions at the close ----
        last = n == len(idx) - 1
        if not trend[i]:
            blocked = False                        # the trend turned down: the next up-turn is a normal entry
        stop_next = None
        if not last:
            if qty and not trend[i]:
                pend_sell = True
            elif qty:
                stop_next = stop_level(stop_kind, stop_val, hh, atr14[i])
            elif trend[i] and not pend_buy:
                ok = not blocked
                if blocked and reentry.startswith("hi") and hc[i - 1] is not None and x["c"] > hc[i - 1]:
                    ok, blocked = True, False
                if ok:
                    pend_buy, pend_qty = True, math.floor(cash / x["c"])
                    hh = x["c"]
                    stop_next = stop_level(stop_kind, stop_val, x["c"], atr14[i])
        st = 2 if (qty and not pend_sell) or pend_buy else 0
        levels.append([st, None, None, round(stop_next, 2) if stop_next else None, round(entry["px"], 2) if entry else None, None, None, None])
        stop_line.append(round(stop_next, 2) if stop_next else None)
    first, lastb = b[idx[0]], b[idx[-1]]
    open_t = None
    if qty:
        open_t = dict(entry_t=entry["t"], entry_px=entry["px"], qty=qty, mark=lastb["c"],
                      pnl=(lastb["c"] - entry["px"]) * qty - entry["fee"], stop=stop_next or 0.0, phase="trend up")
    final = cash + qty * lastb["c"]
    bh_qty = math.floor(CAP0 / first["o"]); bh_cash = CAP0 - bh_qty * first["o"] * (1 + COMM)
    for row in series:
        row.append(round(bh_cash + bh_qty * row[4], 2))
    pk, bh_dd = CAP0, 0.0
    for i in idx:
        pk = max(pk, bh_cash + bh_qty * b[i]["h"]); bh_dd = max(bh_dd, (pk - (bh_cash + bh_qty * b[i]["l"])) / pk * 100)
    return dict(idx=idx, series=series, levels=levels, trades=trades, open=open_t, final_eq=final, maxdd=maxdd,
                maxdd_pct=maxdd_pct, bh_final=bh_cash + bh_qty * lastb["c"], bh_qty=bh_qty, bh_dd=bh_dd,
                first=first, last=lastb, exposure=in_mkt / len(idx) * 100, stop_line=stop_line)


GRID_TREND = [(f, s, bd) for f in (5, 8, 10, 15, 20) for s in (30, 40, 45, 50, 60) for bd in (0.0, 1.0, 2.0) if f < s]
GRID_STOP = ([("none", 0)] + [("trail", p) for p in (6, 8, 10, 12, 15, 20, 25)] + [("atr", k) for k in (1.5, 2.0, 2.5, 3.0, 4.0, 5.0)]
             + [("atrcap", (k, p)) for k in (4.0, 5.0, 6.0) for p in (12, 15, 18, 20, 22, 25)])
GRID_RE = ["fresh", "hi10", "hi20"]


def parse_stop(s):
    if s == "none":
        return "none", 0
    k, v = s.split(":")
    if k == "atrcap":
        a, p = v.split("/"); return k, (float(a), float(p))
    return k, float(v)


if __name__ == "__main__":
    mode, data_dir, sym = sys.argv[1:4]
    start, end = v3.window(sys.argv[4:6]); out_path = sys.argv[6]
    b = v3.load(data_dir, sym); a14 = v3.atr(b, 14)
    trends = {p: trend_band(b, *p) for p in GRID_TREND}
    if mode == "search":
        rows = []
        for p in GRID_TREND:
            tr = trends[p][0]
            for (sk, sv), re_ in itertools.product(GRID_STOP, GRID_RE):
                if sk == "none" and re_ != "fresh":
                    continue
                r = run(b, tr, sk, sv, re_, start, end, a14)
                s = v3.stats(r)
                rows.append(dict(trend=list(p), stop=(f"{sk}:{sv[0]}/{sv[1]}" if sk == "atrcap" else f"{sk}:{sv}") if sk != "none" else "none", re=re_, final=round(s["final_eq"], 2),
                                 maxdd=round(s["maxdd_pct"], 2), trades=s["closed_trades"], exposure=round(s["exposure"], 1),
                                 cagr=s["cagr"], bh=s["bh_final"], bh_dd=s["bh_dd"]))
        json.dump(dict(symbol=sym, start=sys.argv[4], end=sys.argv[5], rows=rows), open(out_path, "w"))
        bh, bdd = rows[0]["bh"], rows[0]["bh_dd"]
        good = [r for r in rows if r["final"] > bh and r["maxdd"] < bdd]
        print(f"{sym} {sys.argv[4]}→{sys.argv[5]}  B&H ${bh:,.0f} dd {bdd:.1f}%  combos {len(rows)}  beat on both {len(good)}")
        for r in sorted(good, key=lambda r: r["maxdd"])[:12]:
            print(f"  {str(r['trend']):<16}{r['stop']:<11}{r['re']:<6} ${r['final']:>10,.0f}  dd {r['maxdd']:5.1f}%  trades {r['trades']:3d}")
    else:
        out = []
        for spec in sys.argv[7].split(";"):
            key, tp, sp, re_, name = spec.split("|")
            p = tuple(float(v) if "." in v else int(v) for v in tp.split(","))
            tr, f, s_ = trend_band(b, *p) if p in trends else trend_band(b, *p)
            sk, sv = parse_stop(sp)
            res = run(b, tr, sk, sv, re_, start, end, a14)
            st = v3.stats(res)
            ser = lambda d: str(d)
            sel = lambda arr: [None if arr[i] is None else round(arr[i], 2) for i in res["idx"]]
            lines = [dict(name=f"SMA {p[0]}", values=sel(f)), dict(name=f"SMA {p[1]}", values=sel(s_))]
            if sk != "none":
                lines.append(dict(name=f"Stop ({fmt_stop(sk, sv)})", values=res["stop_line"]))
            out.append(dict(tf=key, bar="1D", mode="%", name=name, kind="trend", symbol=sym, subject=v3.SUBJECT.get(sym, sym),
                            params=dict(dip=0, wide=0, tgt=0, tight=0, pct=True, reb=0, trend=False),
                            series=res["series"], levels=res["levels"], lines=lines,
                            trades=[{k: (ser(v) if isinstance(v, dt.datetime) else v) for k, v in t.items()} for t in res["trades"]],
                            open=({k: (ser(v) if isinstance(v, dt.datetime) else v) for k, v in res["open"].items()} if res["open"] else None),
                            first=str(res["first"]["t"]), last=str(res["last"]["t"]), **st))
            print(f"{key:<12} ${st['final_eq']:>11,.2f} ({st['net_pct']:+.0f}%)  dd {st['maxdd_pct']:.1f}%  trades {st['closed_trades']}  "
                  f"win {st['winrate'] or 0:.0f}%  in-mkt {st['exposure']:.0f}%   B&H ${st['bh_final']:,.0f} dd {st['bh_dd']:.1f}%")
        json.dump(out, open(out_path, "w"), default=str, separators=(",", ":"))
