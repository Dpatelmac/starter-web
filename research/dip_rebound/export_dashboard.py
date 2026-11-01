"""Turn results/results.json into the small CSV files the dashboard reads.

Writes results/dashboard/*.csv:
  headline.csv   one row per holding period: signals vs any-day baseline vs edge
  splits.csv     3-day edge by condition, full period and in/out-of-sample
  rules.csv      top 15 rules ranked on 2005-2015, with their 2016-2026 result
  portfolio.csv  simulated strategies: CAGR, Sharpe, max drawdown (full and 2016+)
  curves.csv     weekly equity curves for the main strategies (long format)
  by_year.csv    3-day edge per calendar year
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

    for f in sorted(OUT.glob("*.csv")):
        print(f"{f.name:<15} {f.stat().st_size/1024:7.1f} KB")


if __name__ == "__main__":
    main()
