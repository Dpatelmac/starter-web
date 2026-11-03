"""Build the REPORT_META JSON (title, notes, summary tables) for the V4 report.

usage: v4_meta.py <data_dir> <results_dir>   -> prints JSON to stdout
"""
import json, sys, os, datetime as dt, importlib.util

data_dir, res = sys.argv[1:3]
here = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("v4", os.path.join(here, "backtest_v4.py"))
v4 = importlib.util.module_from_spec(spec); sys.argv = ["v4"]; spec.loader.exec_module(v4)
v3 = v4.v3

SETS = [("LITE_3y", "LITE · 3 yrs"), ("LITE_oos", "LITE · 2016–23"), ("COHR_3y", "COHR · 3 yrs"),
        ("AAOI_3y", "AAOI · 3 yrs"), ("CIEN_3y", "CIEN · 3 yrs"), ("NVDA_3y", "NVDA · 3 yrs")]
S = {k: json.load(open(f"{res}/v4search_{k}.json"))["rows"] for k, _ in SETS}
K = lambda r: (tuple(r["trend"]), r["stop"], r["re"])
I = {k: {K(r): r for r in v} for k, v in S.items()}
money = lambda v: f"${v:,.0f}"
both = lambda r: r["final"] > r["bh"] and r["maxdd"] < r["bh_dd"]

CANDS = [("V4 · SMA 8/50 band + 5×ATR stop", ((8, 50, 1.0), "atr:5.0", "hi10")),
         ("SMA 8/50, 2% band + 5×ATR stop", ((8, 50, 2.0), "atr:5.0", "hi10")),
         ("V3 · SMA 8/45 band, no stop", ((8, 45, 1.0), "none", "fresh")),
         ("Low-drawdown fit (SMA 20/45, 5×ATR max 22%)", ((20, 45, 1.0), "atrcap:5.0/22", "fresh"))]

# 1 · every candidate on every set, both criteria
t1 = []
for name, key in CANDS:
    cells = []
    for k, _ in SETS:
        r = I[k][key]
        cells.append(("✓ " if both(r) else "✕ ") + f"{r['final'] / r['bh']:.2f}× · dd {r['maxdd']:.0f}%")
    t1.append([name] + cells + [f"{sum(both(I[k][key]) for k, _ in SETS)}/6"])
t1.append(["Buy & hold"] + [f"{money(I[k][CANDS[0][1]]['bh'])} · dd {I[k][CANDS[0][1]]['bh_dd']:.0f}%" for k, _ in SETS] + ["—"])

# 2 · stop types on LITE 3 yrs with the V4 trend and re-entry
L = I["LITE_3y"]; bh, bdd = S["LITE_3y"][0]["bh"], S["LITE_3y"][0]["bh_dd"]
t2 = []
for sk, label in [("none", "No stop (trend exit only)"), ("trail:10", "10% trailing stop"), ("trail:15", "15% trailing stop"),
                  ("trail:20", "20% trailing stop"), ("trail:25", "25% trailing stop"), ("atr:2.0", "2 × ATR"),
                  ("atr:3.0", "3 × ATR"), ("atr:4.0", "4 × ATR"), ("atr:5.0", "5 × ATR (V4)"),
                  ("atrcap:5.0/20", "5 × ATR, never more than 20%"), ("atrcap:5.0/25", "5 × ATR, never more than 25%")]:
    re_ = "fresh" if sk == "none" else "hi10"
    r = L[((8, 50, 1.0), sk, re_)]
    t2.append([label, money(r["final"]), f"{r['maxdd']:.1f}%", str(r["trades"]), "✓ both" if both(r) else ("✕ profit" if r["final"] <= bh else "✕ drawdown")])

# 3 · start dates (LITE, held to today), both criteria
b = v3.load(data_dir, "LITE"); a = v3.atr(b, 14)
tr4 = v4.trend_band(b, 8, 50, 1.0)[0]; tr3 = v4.trend_band(b, 8, 45, 1.0)[0]
t3, w4, w3, n = [], 0, 0, 0
for y, m in [(2023, mm) for mm in range(5, 13)] + [(2024, mm) for mm in range(1, 13)] + [(2025, mm) for mm in range(1, 7)]:
    st = dt.datetime(y, m, 1, tzinfo=v3.NY); n += 1
    s4 = v3.stats(v4.run(b, tr4, "atr", 5.0, "hi10", st, None, a)); s3 = v3.stats(v4.run(b, tr3, "none", 0, "fresh", st, None, a))
    ok4 = s4["final_eq"] > s4["bh_final"] and s4["maxdd_pct"] < s4["bh_dd"]; ok3 = s3["final_eq"] > s3["bh_final"] and s3["maxdd_pct"] < s3["bh_dd"]
    w4 += ok4; w3 += ok3
    t3.append([st.strftime("%b %Y"), ("✓ " if ok4 else "✕ ") + f"{money(s4['final_eq'])} · dd {s4['maxdd_pct']:.0f}%",
               ("✓ " if ok3 else "✕ ") + f"{money(s3['final_eq'])} · dd {s3['maxdd_pct']:.0f}%",
               f"{money(s4['bh_final'])} · dd {s4['bh_dd']:.0f}%"])
t3.append(["Beats buy & hold on both", f"{w4}/{n} start dates", f"{w3}/{n} start dates", "—"])

# 4 · search size
t4 = [[lab, f"{len(S[k]):,}", str(sum(both(r) for r in S[k])), money(S[k][0]["bh"]), f"{S[k][0]['bh_dd']:.1f}%"] for k, lab in SETS]

meta = dict(
    title="LITE · Daily Trend Strategy V4",
    matrixTitle="Every candidate on every test set (value of $10,000 today)",
    noteTitle="What V4 is: ",
    note=("V3's daily trend rule (fast SMA vs slow SMA with a 1% band, here 8/50) plus a real stop-loss order: a trailing stop "
          "5 × ATR(14) below the highest high since entry, which can fill during the day. After a stop-out it buys again only on a "
          "close above the prior 10-day closing high while the trend is still up. Goal: more profit than buy & hold AND a much "
          f"lower intrabar max drawdown. Picked from {len(S['LITE_3y']):,} settings on LITE's last 3 years and checked on five other "
          "test sets; settings that only work on LITE (like the low-drawdown fit) are shown so you can see why they were not picked."),
    tables=[
        dict(title="Profit and drawdown vs buy & hold on every test set",
             sub="Each cell: strategy value ÷ buy & hold value · strategy max drawdown · ✓ = more profit AND a smaller drawdown than buy & hold",
             head=["Strategy"] + [lab for _, lab in SETS] + ["Wins (both)"], rows=t1, hl=[0]),
        dict(title="Which stop? V4's trend rule on LITE · 3 years with different stop orders",
             sub=f"Buy & hold: {money(bh)}, max drawdown {bdd:.1f}% · tight stops cut drawdown but sell too often and miss the big run",
             head=["Stop order", "Value today", "Max drawdown", "Trades", "vs buy & hold"], rows=t2, hl=[8]),
        dict(title="Does the start date matter? LITE, started on the 1st of each month and held to today",
             sub="Value of $10,000 today · max drawdown · ✓ = more profit AND a smaller drawdown than buy & hold from the same day",
             head=["Start", CANDS[0][0], CANDS[2][0], "Buy & hold"], rows=t3),
        dict(title="How many settings were tried",
             sub="Trend (fast × slow × band) × stop order × re-entry rule · 'beat on both' = more profit and a smaller drawdown than buy & hold",
             head=["Test set", "Settings", "Beat on both", "Buy & hold value", "Buy & hold drawdown"], rows=t4, hl=[0]),
    ])
print(json.dumps(meta))
