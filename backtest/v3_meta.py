"""Build the REPORT_META JSON (title, notes, summary tables) for the V3 report from the search results.

usage: v3_meta.py <data_dir> <results_dir>   -> prints JSON to stdout
"""
import json, math, sys, datetime as dt, importlib.util, os

data_dir, res = sys.argv[1:3]
spec = importlib.util.spec_from_file_location("v3", os.path.join(os.path.dirname(os.path.abspath(__file__)), "backtest_v3.py"))
v3 = importlib.util.module_from_spec(spec); sys.argv = ["v3"]; spec.loader.exec_module(v3)

SETS = [("LITE_3y", "LITE · 3 yrs"), ("LITE_oos", "LITE · 2016–23"), ("COHR_3y", "COHR · 3 yrs"),
        ("AAOI_3y", "AAOI · 3 yrs"), ("CIEN_3y", "CIEN · 3 yrs"), ("NVDA_3y", "NVDA · 3 yrs")]
S = {k: json.load(open(f"{res}/search_{k}.json"))["rows"] for k, _ in SETS}
k0 = lambda r: (r["family"], tuple(r["params"]))
IDX = {k: {k0(r): r for r in v} for k, v in S.items()}
L3 = S["LITE_3y"]; BH = L3[0]["bh"]
money = lambda v: f"${v:,.0f}"
NAMES = {"ema_cross": "EMA cross", "sma_cross": "SMA cross", "above_ema": "Close above EMA", "above_sma": "Close above SMA",
         "donchian": "Donchian breakout", "supertrend": "Supertrend", "roc": "Momentum (ROC)", "macd": "MACD",
         "sma_band": "SMA cross + band", "dd_trail": "Trailing % stop", "chandelier": "Chandelier ATR stop"}

# 1 · family summary on LITE 3y
fam = {}
for r in L3:
    fam.setdefault(r["family"], []).append(r)
t1 = []
for f, rows in sorted(fam.items(), key=lambda kv: -max(r["final"] for r in kv[1])):
    v = sorted(r["final"] for r in rows); best = max(rows, key=lambda r: r["final"])
    t1.append([NAMES[f], len(rows), f"{sum(x > BH for x in v)}", money(best["final"]), str(best["params"]),
               money(v[len(v) // 2]), f"{best['maxdd']:.0f}%"])

# 2 · SMA 1% band heat-table on LITE 3y
g = {(r["params"][0], r["params"][1]): r["final"] for r in L3 if r["family"] == "sma_band" and r["params"][2] == 1.0}
slows = sorted({k[1] for k in g}); fasts = sorted({k[0] for k in g})
t2 = [[f"fast {f}"] + [("✓ " if g[(f, s)] > BH else "✕ ") + money(g[(f, s)]) for s in slows] for f in fasts]

# 3 · validation of the shortlisted strategies
SHORT = [("V3 · SMA 8/45, 1% band", ("sma_band", (8, 45, 1.0))), ("SMA 10/45, 2% band", ("sma_band", (10, 45, 2.0))),
         ("SMA 15/50 cross", ("sma_cross", (15, 50))), ("Supertrend 10/3", ("supertrend", (10, 3.0))),
         ("Donchian 20/15", ("donchian", (20, 15)))]
t3 = []
for name, key in SHORT:
    rat = [IDX[k][key]["final"] / IDX[k][key]["bh"] for k, _ in SETS]
    t3.append([name] + [("✓ " if x > 1 else "✕ ") + f"{x:.2f}×" for x in rat] + [f"{sum(x > 1 for x in rat)}/6"])
t3.append(["Buy & hold"] + [money(IDX[k][SHORT[0][1]]["bh"]) for k, _ in SETS] + ["—"])

# 4 · start-date robustness (LITE, held to today)
b = v3.load(data_dir, "LITE")
wants = {n: v3.FAMILIES[f][0](b, *p)[0] for n, (f, p) in SHORT[:3]}
t4, wins, n = [], {k: 0 for k in wants}, 0
for y, m in [(2023, mm) for mm in range(5, 13)] + [(2024, mm) for mm in range(1, 13)] + [(2025, mm) for mm in range(1, 7)]:
    st = dt.datetime(y, m, 1, tzinfo=v3.NY); n += 1; row = [st.strftime("%b %Y")]; bh = None
    for k, w in wants.items():
        s = v3.stats(v3.simulate(b, w, st, None)); bh = s["bh_final"]; wins[k] += s["final_eq"] > bh
        row.append(("✓ " if s["final_eq"] > bh else "✕ ") + money(s["final_eq"]))
    t4.append(row + [money(bh)])
t4.append(["Beats buy & hold"] + [f"{wins[k]}/{n} start dates" for k in wants] + ["—"])

total = len(L3)
meta = dict(
    title="LITE · Daily Trend Strategy V3",
    matrixTitle="Every shortlisted strategy on every test set",
    noteTitle="What V3 is: ",
    note=("A trend-following rule on the daily chart. Buy when the 8-day simple moving average closes more than 1% above the "
          "45-day average; sell when it closes more than 1% below it (the 1% band stops whipsaws). Signals at the close, "
          f"fills at the next open. It was chosen from {total} settings across {len(fam)} strategy families on LITE's last 3 years, "
          "then checked on LITE 2016–2023 and on COHR, AAOI, CIEN and NVDA. The search itself can flatter the winner, so "
          "read the test-set columns, not just LITE · 3 yrs."),
    tables=[
        dict(title="Strategy families tested on LITE · last 3 years",
             sub=f"$10,000 start · buy & hold ends at {money(BH)} · {total} settings tested in total",
             head=["Family", "Settings", "Beat B&H", "Best value", "Best settings", "Median value", "Best's max drawdown"], rows=t1),
        dict(title="SMA cross with a 1% band: every setting on LITE · last 3 years",
             sub=f"Value of $10,000 today · ✓ beats buy & hold ({money(BH)}) · the good zone is broad, not a single lucky cell",
             head=["Fast \\ slow"] + [f"slow {s}" for s in slows], rows=t2,
             hl=[fasts.index(8)]),
        dict(title="Does it hold up elsewhere? Strategy ÷ buy & hold",
             sub="Above 1.00× beats buy & hold on that test set · LITE · 3 yrs is where the settings were picked; the other five are checks",
             head=["Strategy"] + [lab for _, lab in SETS] + ["Wins"], rows=t3, hl=[0]),
        dict(title="Does the start date matter? LITE, bought on the 1st of each month and held to today",
             sub="Strategy value of $10,000 today vs buying and holding from the same day",
             head=["Start", SHORT[0][0], SHORT[1][0], SHORT[2][0], "Buy & hold"], rows=t4),
    ])
print(json.dumps(meta))
