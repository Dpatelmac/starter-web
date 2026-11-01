"""Portfolio and market snapshot as of the latest close in the local data.
Prices: research/dip_rebound/data (Yahoo Finance) plus a small fetch for
tickers outside it (ARM) and the 13-week T-bill yield (^IRX)."""
import sys, json
from pathlib import Path
import numpy as np, pandas as pd, yfinance as yf
D = Path(__file__).resolve().parent.parent / "dip_rebound" / "data"
HOLD = {"MU": 1, "STX": 1, "META": 1, "ARM": 4, "NVDA": 1, "INTC": 10, "QCOM": 6, "ADI": 3, "PG": 8, "ISRG": 3}
CASH = 15282.17
px = pd.concat([pd.read_parquet(D / "prices.parquet"), pd.read_parquet(D / "holdout_prices.parquet")])
etf = pd.read_parquet(D / "etf.parquet")
uni = pd.read_csv(D / "universe.csv")
missing = [t for t in HOLD if t not in set(px.ticker)]
if missing:
    x = yf.download(missing, start="2025-06-01", auto_adjust=False, progress=False, group_by="ticker")
    for t in missing:
        d = x[t] if isinstance(x.columns, pd.MultiIndex) else x
        d = d.reset_index().rename(columns=str.lower).rename(columns={"adj close": "adj_close"})
        d["ticker"] = t
        px = pd.concat([px, d[["date", "ticker", "open", "high", "low", "close", "adj_close", "volume"]]])
px = px.sort_values(["ticker", "date"])
last = px["date"].max()
print("latest close:", last.date())
rows = []
for t, q in HOLD.items():
    s = px[px.ticker == t].set_index("date")["adj_close"]
    c = px[px.ticker == t].set_index("date")["close"]
    rows.append({"ticker": t, "shares": q, "price": c.iloc[-1], "value": q * c.iloc[-1],
                 "vs_200d": s.iloc[-1] / s.rolling(200).mean().iloc[-1] - 1,
                 "ret_1m": s.iloc[-1] / s.iloc[-22] - 1, "ret_12_1": s.iloc[-22] / s.iloc[-253] - 1 if len(s) > 253 else np.nan,
                 "vol_60d": s.pct_change().iloc[-60:].std() * np.sqrt(252),
                 "sector": (uni.set_index("ticker")["sector"].get(t, "Information Technology (ARM)"))})
h = pd.DataFrame(rows)
nav = CASH + h["value"].sum()
h["weight"] = h["value"] / nav
print(f"NAV ${nav:,.0f}  invested {h['value'].sum()/nav:.1%}  cash {CASH/nav:.1%}")
print(h.round(3).to_string(index=False))
print("by sector:", (h.groupby("sector")["value"].sum() / h["value"].sum()).round(3).to_dict())
# Correlation / risk of the stock sleeve
ret = px[px.ticker.isin(HOLD)].pivot(index="date", columns="ticker", values="adj_close").pct_change().iloc[-120:]
w = h.set_index("ticker")["value"] / h["value"].sum()
port = (ret[w.index] * w).sum(axis=1)
spy = etf[etf.ticker == "SPY"].set_index("date")["adj_close"]
sr = spy.pct_change().reindex(port.index)
beta = np.cov(port.dropna(), sr.dropna())[0, 1] / sr.var()
print(f"stock sleeve: 120d vol {port.std()*np.sqrt(252):.1%}, beta vs SPY {beta:.2f}, avg pairwise corr {ret.corr().values[np.triu_indices(len(w),1)].mean():.2f}")
# Market
vix = etf[etf.ticker == "^VIX"].set_index("date")["close"]
def stat(t):
    s = etf[etf.ticker == t].set_index("date")["adj_close"]
    return s.iloc[-1] / s.rolling(200).mean().iloc[-1] - 1, s.iloc[-1] / s.iloc[-22] - 1, s.iloc[-1] / s.cummax().iloc[-1] - 1
for t in ["SPY", "XLK", "XLV", "XLF", "XLE", "XLU", "XLI", "XLP"]:
    a, b, c = stat(t); print(f"{t}: vs 200d {a:+.1%}  1m {b:+.1%}  from high {c:+.1%}")
print(f"VIX {vix.iloc[-1]:.1f} (1y median {vix.iloc[-252:].median():.1f})")
sp = px[px.ticker.isin(uni.ticker)].copy()
sp["sma200"] = sp.groupby("ticker")["adj_close"].transform(lambda s: s.rolling(200).mean())
lastd = sp[sp.date == last]
print(f"S&P 500/400 breadth: {(lastd.adj_close > lastd.sma200).mean():.1%} above 200d")
spyc = spy.iloc[-1]; print(f"SPY {spyc:.2f}, 200d {spy.rolling(200).mean().iloc[-1]:.2f}, 10d chg {spy.iloc[-1]/spy.iloc[-11]-1:+.1%}")
irx = yf.download("^IRX", start="2004-01-01", progress=False, auto_adjust=False)
irx = irx["Close"].squeeze() if "Close" in irx else irx.squeeze()
irx.rename("irx").to_frame().to_parquet(D / "irx.parquet")
print(f"13-week T-bill yield: {float(irx.iloc[-1]):.2f}% (rows {len(irx)})")
