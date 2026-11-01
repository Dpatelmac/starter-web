"""Download the universe and daily price history for the dip-rebound backtest.

Universe: current S&P 500 + S&P 400 constituents (Wikipedia), plus the S&P 500
"date added" and the S&P 400 change log, so the backtest only counts a stock
from the date it joined an index (see backtest.py).
Prices: daily OHLCV from Yahoo Finance via yfinance, 2004-01-01 to today
(2004 gives the 200-day average a year of warm-up before the 2005 start).

Outputs (in ./data, git-ignored):
  universe.csv        ticker, name, sector, index, sp500_added
  sp400_changes.csv   date, added, removed  (S&P 400 change log)
  prices.parquet      long table: date, ticker, open, high, low, close,
                      adj_close, volume
  etf.parquet         same layout for SPY, sector ETFs and ^VIX
"""

from __future__ import annotations

import io
import sys
import time
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
START = "2004-01-01"
UA = {"User-Agent": "Mozilla/5.0 (research script)"}

# Sector ETF for each GICS sector, used for the sector-wide vs idiosyncratic split.
SECTOR_ETF = {
    "Information Technology": "XLK",
    "Health Care": "XLV",
    "Financials": "XLF",
    "Consumer Discretionary": "XLY",
    "Consumer Staples": "XLP",
    "Industrials": "XLI",
    "Energy": "XLE",
    "Utilities": "XLU",
    "Real Estate": "XLRE",  # starts 2015; backtest falls back to SPY before that
    "Materials": "XLB",
    "Communication Services": "XLC",  # starts 2018; falls back to SPY before that
}
EXTRA = ["SPY", "^VIX"] + sorted(set(SECTOR_ETF.values()))


def read_wiki_tables(url: str) -> list[pd.DataFrame]:
    html = requests.get(url, headers=UA, timeout=30).text
    return pd.read_html(io.StringIO(html))


def yahoo_symbol(sym: str) -> str:
    return sym.strip().replace(".", "-")


def fetch_universe() -> pd.DataFrame:
    sp500_tables = read_wiki_tables(
        "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    )
    sp500 = sp500_tables[0]
    sp500 = pd.DataFrame(
        {
            "ticker": sp500["Symbol"].map(yahoo_symbol),
            "name": sp500["Security"],
            "sector": sp500["GICS Sector"],
            "index": "SP500",
            "sp500_added": pd.to_datetime(sp500["Date added"], errors="coerce", format="mixed"),
        }
    )

    sp400_tables = read_wiki_tables(
        "https://en.wikipedia.org/wiki/List_of_S%26P_400_companies"
    )
    sp400 = sp400_tables[0]
    sp400 = pd.DataFrame(
        {
            "ticker": sp400["Symbol"].map(yahoo_symbol),
            "name": sp400["Security"],
            "sector": sp400["GICS Sector"],
            "index": "SP400",
        }
    )

    # S&P 400 change log (Date | Added ticker | Removed ticker | Reason).
    ch = next(t for t in sp400_tables if isinstance(t.columns, pd.MultiIndex))
    ch.columns = ["_".join(c).lower() for c in ch.columns]
    changes = pd.DataFrame(
        {
            "date": pd.to_datetime(ch["date_date"], errors="coerce", format="mixed"),
            "added": ch["added_ticker"].map(lambda s: yahoo_symbol(s) if isinstance(s, str) else None),
            "removed": ch["removed_ticker"].map(lambda s: yahoo_symbol(s) if isinstance(s, str) else None),
        }
    ).dropna(subset=["date"])
    changes.to_csv(DATA / "sp400_changes.csv", index=False)
    print(f"S&P 400 change log: {len(changes)} rows, {changes.date.min().date()} to {changes.date.max().date()}")

    uni = pd.concat([sp500, sp400], ignore_index=True).drop_duplicates("ticker")
    uni.to_csv(DATA / "universe.csv", index=False)
    print(f"universe: {len(sp500)} S&P 500 + {len(sp400)} S&P 400 -> {len(uni)} tickers; "
          )
    return uni


def download(tickers: list[str], chunk: int = 80) -> pd.DataFrame:
    frames = []
    for i in range(0, len(tickers), chunk):
        batch = tickers[i : i + chunk]
        for attempt in range(4):
            try:
                df = yf.download(
                    batch, start=START, auto_adjust=False, actions=False,
                    group_by="ticker", threads=True, progress=False,
                )
                break
            except Exception as exc:  # network hiccup: back off and retry
                wait = 2 ** (attempt + 1)
                print(f"  batch {i}: {exc!r}, retry in {wait}s", file=sys.stderr)
                time.sleep(wait)
        else:
            continue
        long = (
            df.stack(level=0, future_stack=True)
            .rename_axis(["date", "ticker"])
            .reset_index()
        )
        long.columns = [str(c).lower().replace(" ", "_") for c in long.columns]
        long = long.dropna(subset=["close"])
        frames.append(long)
        print(f"  {min(i + chunk, len(tickers))}/{len(tickers)} tickers downloaded")
    out = pd.concat(frames, ignore_index=True)
    return out[["date", "ticker", "open", "high", "low", "close", "adj_close", "volume"]]


def main() -> None:
    DATA.mkdir(exist_ok=True)
    uni = fetch_universe()

    print("downloading ETFs / VIX ...")
    etf = download(EXTRA)
    etf.to_parquet(DATA / "etf.parquet", index=False)

    print("downloading stocks ...")
    px = download(uni["ticker"].tolist())
    px.to_parquet(DATA / "prices.parquet", index=False)
    got = px["ticker"].nunique()
    missing = sorted(set(uni["ticker"]) - set(px["ticker"]))
    print(f"stocks with data: {got}/{len(uni)}; rows: {len(px):,}; missing: {missing[:20]}")


if __name__ == "__main__":
    main()
