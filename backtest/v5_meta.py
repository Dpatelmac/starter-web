"""Build the REPORT_META JSON for the V5 report (4H and two-stage-stop checks against daily V4).

usage: v5_meta.py <results_dir>   -> prints JSON to stdout
"""
import json, sys

res = sys.argv[1]
SYMS = ["LITE", "COHR", "AAOI", "CIEN", "NVDA"]
money = lambda v: f"${v:,.0f}"
REP = {s: json.load(open(f"{res}/rep_{s}.json")) for s in SYMS}
both = lambda r: r["final_eq"] > r["bh_final"] and r["maxdd_pct"] < r["bh_dd"]

t1 = []
for j, r0 in enumerate(REP["LITE"]):
    cells = [("✓ " if both(REP[s][j]) else "✕ ") + f"{REP[s][j]['final_eq'] / REP[s][j]['bh_final']:.2f}× · dd {REP[s][j]['maxdd_pct']:.0f}%" for s in SYMS]
    t1.append([r0["name"]] + cells + [f"{sum(both(REP[s][j]) for s in SYMS)}/5"])
t1.append(["Buy & hold"] + [f"{money(REP[s][0]['bh_final'])} · dd {REP[s][0]['bh_dd']:.0f}%" for s in SYMS] + ["—"])

t2 = []
for label, f in [("4H · trend + stop (SMA band, Supertrend, Donchian)", "search_LITE.json"),
                 ("4H · SMA band + two-stage ATR stop", "two_4H_LITE.json"),
                 ("1D · SMA band + two-stage ATR stop", "two_1D_LITE.json")]:
    R = json.load(open(f"{res}/{f}"))["rows"]; bh = R[0]["bh"]
    row = [label, f"{len(R):,}", str(sum(r['final'] > bh and r['maxdd'] < r['bh_dd'] for r in R))]
    for cap in (30, 27, 25):
        sub = [r for r in R if r["maxdd"] < cap and r["final"] > bh]
        row.append(f"{len(sub)}" + (f" (best {money(max(r['final'] for r in sub))})" if sub else ""))
    t2.append(row)

meta = dict(
    title="LITE · 4H and Two-Stage Stop Checks (V5)",
    matrixTitle="Every candidate on every stock (value of $10,000 today)",
    noteTitle="What V5 tested: ",
    note=("Can a 4H chart, or a two-stage stop (wide until the trade is up g%, then tighter), beat daily V4: profit above buy & hold "
          "with a lower drawdown than V4's ~30%? Tools were limited to trend rules plus stop-loss orders. All five stocks use the same "
          "window, 6 Dec 2023 → 3 Nov 2026 (hourly data starts there). Answer: no. Daily V4 stays the best; about 30% is the lowest "
          "drawdown on LITE that still keeps profit above buy & hold."),
    tables=[
        dict(title="Profit and drawdown vs buy & hold on every stock (6 Dec 2023 → 3 Nov 2026)",
             sub="Each cell: strategy value ÷ buy & hold · strategy max drawdown · ✓ = more profit AND a smaller drawdown than buy & hold",
             head=["Strategy"] + SYMS + ["Wins (both)"], rows=t1, hl=[0]),
        dict(title="Is there anything below V4's ~30% drawdown on LITE? Settings that keep profit above buy & hold",
             sub="Counts of settings on LITE that beat buy & hold on profit and have a max drawdown below each limit",
             head=["Search", "Settings", "Beat B&H on both", "Drawdown < 30%", "< 27%", "< 25%"], rows=t2),
    ])
print(json.dumps(meta))
