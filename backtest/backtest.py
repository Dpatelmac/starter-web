"""Bar-by-bar replica of lite_dip_rebound_two_stage_trail.pine with TradingView-style fills.

- Orders are generated at bar close; market entry fills at next bar open.
- Stop exit (replaced each bar) fills at open if the bar opens through it, else at the stop.
- Commission 0.1% per side, slippage 0, qty = floor(100% equity / close at signal bar).
"""
import json, math, sys, datetime as dt
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
# usage: backtest.py <data_dir> <start YYYY-MM-DD> <out.json> <tf,tf,...>
DATA = sys.argv[1]
START = dt.datetime.fromisoformat(sys.argv[2]).replace(tzinfo=dt.timezone.utc)
OUT = sys.argv[3]
TFS = sys.argv[4].split(",")
CAP0 = 10000.0
COMM = 0.001
REB = 0.5                                  # rebound off the low, % (same in both modes)
MODES = {                                  # Pine input "Amounts in": Dollar (flowchart) or Percent
    "$": dict(dip=60.0, wide=95.0, tgt=60.0, tight=10.0, pct=False),
    "%": dict(dip=6.0, wide=9.5, tgt=6.0, tight=1.0, pct=True),
}
P = MODES["$"]


def dip_level(hi):  return hi * (1 - P["dip"] / 100) if P["pct"] else hi - P["dip"]
def tgt_level(bp):  return bp * (1 + P["tgt"] / 100) if P["pct"] else bp + P["tgt"]
def wide_stop(hi):  return hi * (1 - P["wide"] / 100) if P["pct"] else hi - P["wide"]
def tight_stop(hi): return hi * (1 - P["tight"] / 100) if P["pct"] else hi - P["tight"]


def load(iv):
    r = json.load(open(f"{DATA}/LITE_{iv}.json"))["chart"]["result"][0]
    q = r["indicators"]["quote"][0]
    bars = []
    for i, t in enumerate(r["timestamp"]):
        o, h, l, c = q["open"][i], q["high"][i], q["low"][i], q["close"][i]
        if None in (o, h, l, c):
            continue
        bars.append(dict(t=dt.datetime.fromtimestamp(t, NY), o=o, h=h, l=l, c=c))
    return bars


def to_nh(bars1h, n):
    """TradingView session-aligned N-hour bars for US stocks, anchored at 09:30
    (4H: 09:30-13:30, 13:30-16:00 · 2H: 09:30-11:30, 11:30-13:30, 13:30-15:30, 15:30-16:00)."""
    out = {}
    for b in bars1h:
        seg = max(0, (b["t"].hour * 60 + b["t"].minute) - 570) // (60 * n)
        k = (b["t"].date(), seg)
        if k not in out:
            out[k] = dict(b)
        else:
            a = out[k]; a["h"] = max(a["h"], b["h"]); a["l"] = min(a["l"], b["l"]); a["c"] = b["c"]
    return list(out.values())


def r2(x):
    return None if x is None else round(x, 2)


def run(bars):
    cash, qty = CAP0, 0
    state, tH, tL, buy, trH, stop = 0, None, None, None, None, None
    pend_entry_qty, pend_stop = None, None
    trades, entry = [], None
    eq_curve, peak, maxdd, maxdd_pct = [], CAP0, 0.0, 0.0
    bars = [b for b in bars if b["t"] >= START.astimezone(NY)]
    series, levels = [], []
    for b in bars:
        just_sold = False
        # ---- broker: fills at this bar ----
        if pend_entry_qty:
            px = b["o"]; qty = pend_entry_qty; fee = qty * px * COMM
            cash -= qty * px + fee
            entry = dict(t=b["t"], px=px, qty=qty, fee=fee, hi=b["h"], lo=b["l"])
            pend_entry_qty = None
        if qty and pend_stop is not None and b["l"] <= pend_stop:
            px = b["o"] if b["o"] <= pend_stop else pend_stop
            fee = qty * px * COMM
            cash += qty * px - fee
            entry["hi"] = max(entry["hi"], b["h"]); entry["lo"] = min(entry["lo"], b["l"])
            pnl = (px - entry["px"]) * qty - entry["fee"] - fee
            trades.append(dict(entry_t=entry["t"], entry_px=entry["px"], exit_t=b["t"], exit_px=px, qty=qty,
                               pnl=pnl, pct=pnl / (entry["px"] * qty) * 100,
                               reason="tight trail (after target)" if state == 3 else "wide trail",
                               runup=(entry["hi"] - entry["px"]) * qty, dd=(entry["lo"] - entry["px"]) * qty))
            qty, entry, just_sold = 0, None, True
        elif qty:
            entry["hi"] = max(entry["hi"], b["h"]); entry["lo"] = min(entry["lo"], b["l"])
        pend_stop = None
        # ---- intrabar equity drawdown (TradingView style: uses bar lows while long) ----
        eq_close = cash + qty * b["c"]
        eq_low = cash + qty * b["l"]
        peak = max(peak, cash + qty * b["h"]) if qty else max(peak, eq_close)
        maxdd = max(maxdd, peak - min(eq_low, eq_close)); maxdd_pct = max(maxdd_pct, (peak - min(eq_low, eq_close)) / peak * 100)
        eq_curve.append(eq_close)
        series.append([int(b["t"].timestamp()), round(b["o"],2), round(b["h"],2), round(b["l"],2), round(b["c"],2), round(eq_close,2)])
        # ---- script at bar close ----
        if just_sold:
            state, tH, tL, buy, trH, stop = 0, b["c"], None, None, None, None
            levels.append([0, r2(tH), None, None, None, None, r2(dip_level(tH))])
            continue
        if state == 0:
            tH = b["h"] if tH is None else max(tH, b["h"])
            if b["l"] <= dip_level(tH):
                state, tL = 1, b["l"]
        elif state == 1:
            tL = min(tL, b["l"])
        if state == 1 and b["c"] >= tL * (1 + REB / 100):
            pend_entry_qty = math.floor(cash / b["c"])
            state, buy, trH, stop = 2, None, b["c"], wide_stop(b["c"])
        elif state in (2, 3) and qty:
            first = buy is None
            if first:
                buy = entry["px"]
            if state == 2 and b["h"] >= tgt_level(buy):
                state, trH = 3, b["h"]
            else:
                trH = b["h"] if first else max(trH, b["h"])
            stop = tight_stop(trH) if state == 3 else wide_stop(trH)
        if state in (2, 3):
            pend_stop = stop
        levels.append([state, r2(tH) if state == 0 else None, r2(tL) if state == 1 else None,
                       r2(stop) if state in (2, 3) else None, r2(buy) if state in (2, 3) else None,
                       r2(tgt_level(buy)) if state == 2 and buy is not None else None,
                       r2(dip_level(tH)) if state == 0 and tH is not None else None])
    last = bars[-1]
    open_pnl = None
    if qty:
        open_pnl = dict(entry_t=entry["t"], entry_px=entry["px"], qty=qty, mark=last["c"],
                        pnl=(last["c"] - entry["px"]) * qty - entry["fee"], stop=stop,
                        phase="tight trail" if state == 3 else "wide trail")
    final_eq = cash + qty * last["c"]
    bh_qty = math.floor(CAP0 / bars[0]["o"])
    bh = bh_qty * (last["c"] - bars[0]["o"]) - bh_qty * bars[0]["o"] * COMM
    bh_cash = CAP0 - bh_qty * bars[0]["o"] * (1 + COMM)
    for row in series:
        row.append(round(bh_cash + bh_qty * row[4], 2))
    return dict(series=series, levels=levels, bh_qty=bh_qty, bars=len(bars), first=bars[0]["t"], last=last["t"], trades=trades, open=open_pnl,
                final_eq=final_eq, maxdd=maxdd, maxdd_pct=maxdd_pct, bh=bh,
                bh_pct=bh / CAP0 * 100, first_px=bars[0]["o"], last_px=last["c"],
                state=state, tH=tH, tL=tL)


def report(name, res):
    tr = res["trades"]
    wins = [t for t in tr if t["pnl"] > 0]; losses = [t for t in tr if t["pnl"] <= 0]
    gp = sum(t["pnl"] for t in wins); gl = -sum(t["pnl"] for t in losses)
    closed = sum(t["pnl"] for t in tr)
    net = res["final_eq"] - CAP0
    return dict(tf=name, bars=res["bars"], first=str(res["first"]), last=str(res["last"]),
                net=net, net_pct=net / CAP0 * 100, closed=closed, closed_trades=len(tr),
                wins=len(wins), losses=len(losses),
                winrate=(len(wins) / len(tr) * 100) if tr else None,
                gp=gp, gl=gl, pf=(gp / gl) if gl else None,
                avg=(closed / len(tr)) if tr else None,
                avg_win=(gp / len(wins)) if wins else None, avg_loss=(-gl / len(losses)) if losses else None,
                maxdd=res["maxdd"], maxdd_pct=res["maxdd_pct"], bh=res["bh"], bh_pct=res["bh_pct"],
                first_px=res["first_px"], last_px=res["last_px"],
                trades=[{k: (str(v) if isinstance(v, dt.datetime) else v) for k, v in t.items()} for t in tr],
                open=({k: (str(v) if isinstance(v, dt.datetime) else v) for k, v in res["open"].items()} if res["open"] else None),
                state=res["state"], tH=res["tH"], tL=res["tL"], final_eq=res["final_eq"], bh_final=CAP0 + res["bh"],
                series=res["series"], levels=res["levels"], bh_qty=res["bh_qty"])


if __name__ == "__main__":
    def bars_for(tf):
        if tf == "1D":
            return load("1d")
        if tf.endswith("H") and tf != "1H":
            return to_nh(load("1h"), int(tf[:-1]))
        return load(tf.lower() if tf == "1H" else tf)
    out = []
    for spec in TFS:                       # "1D" (dollar) or "1D:%" (percent)
        tf, mode = (spec.split(":") + ["$"])[:2]
        P = MODES[mode]
        r = report(f"{tf} {mode}" if ":" in spec else tf, run(bars_for(tf)))
        r["bar"], r["mode"], r["params"] = tf, mode, dict(P, reb=REB)
        out.append(r)
    json.dump(out, open(OUT, "w"), default=str, separators=(",", ":"))
    for r in out:
        print(f"{r['tf']:>4} bars={r['bars']:5d} net={r['net']:9.2f} ({r['net_pct']:6.2f}%) trades={r['closed_trades']} "
              f"win={r['winrate']} pf={r['pf']} maxDD={r['maxdd']:.2f} ({r['maxdd_pct']:.2f}%) open={'Y' if r['open'] else 'N'} "
              f"state={r['state']} tH={r['tH']} tL={r['tL']}")
        for t in r["trades"]:
            print("     ", t["entry_t"][:16], f"{t['entry_px']:.2f}", "->", t["exit_t"][:16], f"{t['exit_px']:.2f}",
                  t["qty"], f"{t['pnl']:.2f}", f"{t['pct']:.2f}%", t["reason"])
        if r["open"]:
            print("      OPEN", r["open"])
    print("B&H", out[0]["bh"], out[0]["bh_pct"], out[0]["first_px"], out[0]["last_px"])
