"""Turn results/results.json into the small CSV files the dashboard reads.

Writes results/dashboard/*.csv:
  headline.csv   one row per holding period: signals vs any-day baseline vs edge
  splits.csv     3-day edge by condition, full period and in/out-of-sample
  rules.csv      top 15 rules ranked on 2005-2015, with their 2016-2026 result
  portfolio.csv  simulated strategies: CAGR, Sharpe, max drawdown (full and 2016+)
  curves.csv     weekly equity curves for the main strategies (long format)
  by_year.csv    3-day edge per calendar year
  holdout.csv    pre-registered holdout rules on new stocks vs S&P 500/400
  sweep.csv      510 drop-size combinations x three samples
  pullback.csv   account check of the 5-day pullback at 0/2/5 bps
  weekly.csv     36 weekly pullback portfolio variants (pre-registered test 2)
  weekly_spy.csv SPY buy and hold for each sample of the weekly test
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "results" / "dashboard"
IS_LABEL, OOS_LABEL = "2005-2015 (in-sample)", "2016-2026 (out-of-sample)"


def main() -> None:
    res = json.loads((HERE / "results" / "results.json").read_text())
    OUT.mkdir(parents=True, exist_ok=True)

    o, b = res["overall"], res["baseline"]
    pd.DataFrame([{
        "hold": h, "signals": o["n"], "signal_days": o["days"],
        "dip_raw": o[f"h{h}"]["mean"], "anyday_raw": b[f"h{h}"]["mean"],
        "edge": o[f"h{h}"]["edge"], "t_stat": o[f"h{h}"]["t"], "win_rate": o[f"h{h}"]["win"],
    } for h in res["params"]["holds"]]).to_csv(OUT / "headline.csv", index=False)

    rows = []
    for key, sp in res["splits"].items():
        if key == "period":
            continue
        per = {p: {r["bucket"]: r for r in lst} for p, lst in sp["by_period"].items()}
        for i, r in enumerate(sp["rows"]):
            if r["bucket"] == "n/a":
                continue
            a, z = per.get(IS_LABEL, {}).get(r["bucket"]), per.get(OOS_LABEL, {}).get(r["bucket"])
            rows.append({
                "split": sp["title"], "bucket": r["bucket"], "order": i, "signals": r["n"],
                "edge": r["h3"]["edge"], "t_stat": r["h3"]["t"],
                "edge_is": a["h3"]["edge"] if a else None, "t_is": a["h3"]["t"] if a else None,
                "edge_oos": z["h3"]["edge"] if z else None, "t_oos": z["h3"]["t"] if z else None,
                "win_rate": r["h3"]["win"],
            })
    pd.DataFrame(rows).to_csv(OUT / "splits.csv", index=False)

    pd.DataFrame([{
        "rank": i + 1, "rule": r["rule"], "signals_is": r["n_is"], "edge_is": r["edge_is"], "t_is": r["t_is"],
        "signals_oos": r["n_oos"], "edge_oos": r["edge_oos"], "t_oos": r["t_oos"],
    } for i, r in enumerate(res["rules"][:15])]).to_csv(OUT / "rules.csv", index=False)

    pd.DataFrame([{
        "strategy": k, "hold_days": v["hold"], "cost_bps_side": v["cost_bps_side"], "hedged": v["hedged"],
        "cagr": v["full"]["cagr"], "sharpe": v["full"]["sharpe"], "max_dd": v["full"]["max_dd"],
        "cagr_2016": v["oos"]["cagr"], "sharpe_2016": v["oos"]["sharpe"], "max_dd_2016": v["oos"]["max_dd"],
    } for k, v in res["portfolio"].items()]).to_csv(OUT / "portfolio.csv", index=False)

    cr = []
    for name, c in res["curves"].items():
        cr += [{"date": d, "strategy": name, "value": v} for d, v in zip(c["dates"], c["values"])]
    pd.DataFrame(cr).to_csv(OUT / "curves.csv", index=False)

    pd.DataFrame([{
        "year": y["year"], "signals": y["n"], "edge": y["edge3"], "t_stat": y["t3"],
        "dip_raw": y["r3"], "anyday_raw": y["base_r3"], "win_rate": y["win3"],
    } for y in res["by_year"]]).to_csv(OUT / "by_year.csv", index=False)

    export_followups(res)
    for f in sorted(OUT.glob("*.csv")):
        print(f"{f.name:<15} {f.stat().st_size/1024:7.1f} KB")


RULE_LABELS = {
    "H1": "Down 5%+ in prior week and S&P down 1%+ that day",
    "H2": "Down 5%+ in prior week",
    "H3": "S&P down 1%+ that day",
    "H0": "Every 2%+ drop",
}


def export_followups(res: dict) -> None:
    R = HERE / "results"
    if (R / "holdout.json").exists():
        h = json.loads((R / "holdout.json").read_text())
        rows = []
        for uni, block in [("New stocks", h["rules"]), ("S&P 500/400", h["reference_sp1500ish"])]:
            for k, r in block.items():
                hid = k.split(":")[0]
                rows.append({"id": hid, "rule": RULE_LABELS[hid], "universe": uni, "signals": r["signals"],
                             "edge": r["edge"], "t_stat": r["t"], "edge_2005_15": r["edge_is"],
                             "edge_2016_26": r["edge_oos"], "raw3": r["raw3"], "win_rate": r["win3"],
                             "net_cagr": r["port_net"]["cagr"]})
        pd.DataFrame(rows).to_csv(OUT / "holdout.csv", index=False)

    if (R / "sweep_combined.csv").exists():
        sw = pd.read_csv(R / "sweep_combined.csv")
        lab = lambda r: f"{r['cutoff']*100:g}%" if r["unit"] == "pct" else f"{r['cutoff']:g}x"
        out = pd.DataFrame({
            "combo": sw["measure"] + "|" + sw["cutoff"].map(lambda v: f"{v:g}") + "|" + sw["hold"].astype(str) + "|" + sw["volume"],
            "measure": sw["measure_label"], "cutoff": sw["cutoff"], "cutoff_label": sw.apply(lab, axis=1),
            "hold": sw["hold"], "volume": sw["volume"],
            "edge_sp_2005_15": sw["edge: S&P 2005-15"], "t_sp_2005_15": sw["t: S&P 2005-15"],
            "edge_sp_2016_26": sw["edge: S&P 2016-26"], "t_sp_2016_26": sw["t: S&P 2016-26"],
            "edge_new": sw["edge: New stocks"], "t_new": sw["t: New stocks"], "robust": sw["robust"],
        })
        out.to_csv(OUT / "sweep.csv", index=False, float_format="%.6f")

    if (R / "pullback_check.json").exists():
        pc = json.loads((R / "pullback_check.json").read_text())
        spy = res["portfolio"]["SPY buy & hold"]["full"]
        rows = []
        for k, v in pc.items():
            uni, name, hold, cost = [x.strip() for x in k.split("|")]
            if name not in ("5-day drop 2%+", "All eligible stocks (benchmark)") or hold != "5d":
                continue
            c = int(cost.replace("bps", ""))
            label = "Pullback strategy" if name.startswith("5-day") else "Same schedule, all stocks"
            rows.append({"universe": uni, "strategy": label, "cost_bps": c, "cagr": v["full"]["cagr"],
                         "sharpe": v["full"]["sharpe"], "max_dd": v["full"]["max_dd"]})
        for uni in ("S&P 500/400", "New stocks"):
            for c in (0, 2, 5):
                rows.append({"universe": uni, "strategy": "SPY buy & hold", "cost_bps": c, "cagr": spy["cagr"],
                             "sharpe": spy["sharpe"], "max_dd": spy["max_dd"]})
        pd.DataFrame(rows).to_csv(OUT / "pullback.csv", index=False)

    if (R / "weekly.json").exists():
        wk = json.loads((R / "weekly.json").read_text())
        samples = {"S&P 2005-15": "sp_2005_15", "S&P 2016-26": "sp_2016_26", "New stocks 2005-26": "new"}
        rows = []
        for v in wk["variants"]:
            name = v["variant"]
            r = {"variant": name, "kind": "benchmark" if v["n"] is None else "variant",
                 "turnover": v["turnover_per_year_sp | 5bps"], "beats_spy_samples": v["samples_beating_spy_5bps"],
                 "passes": v["pass"]}
            for s, k in samples.items():
                r[f"cagr_{k}"] = v[f"{s} | 5bps | cagr"]
                r[f"sharpe_{k}"] = v[f"{s} | 5bps | sharpe"]
                r[f"cagr10_{k}"] = v[f"{s} | 10bps | cagr"]
            rows.append(r)
        pd.DataFrame(rows).to_csv(OUT / "weekly.csv", index=False, float_format="%.6f")
        pd.DataFrame([{"sample": s, "key": k, "cagr": wk["spy"][s]["cagr"], "sharpe": wk["spy"][s]["sharpe"],
                       "max_dd": wk["spy"][s]["max_dd"]} for s, k in samples.items()]).to_csv(OUT / "weekly_spy.csv", index=False)


if __name__ == "__main__":
    main()
