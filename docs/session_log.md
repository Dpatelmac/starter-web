# Session log (3 Nov 2026)

What was asked and what was done, in order. Numbers are in `LITE_strategy_findings.md`.

1. **Flowchart → Pine v6 strategy.** Converted the flowchart (`flowchart.jpg`) into
   `pinescript/lite_dip_rebound_two_stage_trail.pine`, following the owner's Pine rules (see `CLAUDE.md`):
   a state machine, a manually trailed stop replaced every bar, plots for every level, and Start/End Date filters.
2. **Backtest, past month, many timeframes.** Signum's backtester only runs its own strategies, so a Python replica
   (`backtest/backtest.py`) was written and run on Yahoo data: 1D, 4H, 1H, 30m, 15m, 5m and 2m. Every timeframe
   lost money (−13% to −32%) but beat buy & hold (−37%).
3. **Value of $10k + interactive offline page.** Built `backtest/LITE_backtest_report.html` (no external
   libraries) with an ending-value chart, equity curves, a price chart with trades and stops, drawdown, and tables.
4. **6-month backtest.** Sub-hour data isn't available that far back, so 1D/4H/2H/1H were tested. Only 1D made money (+12.8%).
   Added zoom, trade details in the tooltip, and label thinning. Report: `LITE_backtest_report_6M.html`.
5. **4-year backtest (owner chose: run both modes; 1D for 4 years + intraday since Dec 2023; add a Pine toggle).**
   Added the "Amounts in: Dollar / Percent" input to the V1 Pine script (Dollar stays default). Dollar mode didn't
   trade until Dec 2025. Best: 4H Percent, +344%. Buy & hold: +840% (4 years) and +1,512% (since Dec 2023).
   Report: `LITE_backtest_report_4Y.html` (two switchable windows, log scale, year-aware dates).
6. **Conclusion in simple words.** The strategy made money long-term but far less than buy & hold on a stock that
   rose 10–16×. Percent mode beats Dollar mode, and drawdowns of 40–60% are normal for it.
7. **V2: try (1) a 200-day trend filter and (2) a 3–5% tight trail.** New files: `..._v2.pine`, `backtest_v2.py`,
   `LITE_backtest_report_V2.html`. The wider trail helped intraday (4H 3%: $67.8k vs $44.4k), but the trend filter
   hurt almost everywhere, so the V2 script ships with the filter off and a 3% trail.
8. **Why LITE flew in 2025–2026.** AI data centers' demand for optical lasers and transceivers (EMLs, 800G/1.6T),
   results that kept beating estimates, co-packaged optics wins, Nasdaq-100 inclusion and momentum. Then a ~37% drop
   in Oct 2026. Sources are listed in the findings doc.
9. **Storage.** Everything is on the `LITE-research` branch (kept separate from `master`, not merged). The data snapshot,
   rebuild and fetch scripts, report checker, this log and `CLAUDE.md` were added so a new session can continue.
10. **V3: find a 1D strategy that beats buy & hold on LITE over 3 years.** Built `backtest/backtest_v3.py`
    (indicators ported from TradingView's built-ins) and searched 412 settings in 11 trend families on LITE 3 Nov
    2023 → 3 Nov 2026, then checked them on LITE 2016–2023 and on COHR, AAOI, CIEN and NVDA (data:
    `backtest/data/2026-11-03-daily/`). Pick: **SMA 8/45 with a 1% band**, $213k vs buy & hold $165k, drawdown
    40% vs 56%, beat buy & hold from all 26 monthly start dates, and beat it in 4 of 6 test sets (lost on
    LITE 2016–2023 and NVDA). New files: `pinescript/lite_daily_trend_v3.pine`, `backtest/v3_meta.py`,
    `backtest/LITE_backtest_report_V3.html`. The template gained generic indicator lines and summary tables.
11. **V4: more profit AND lower drawdown than buy & hold** (owner chose: much lower drawdown; LITE 3 years + checks;
    stop-loss orders allowed; intrabar drawdown). `backtest/backtest_v4.py` searched 7,050 settings (V3 trend × 23
    stop orders × 3 re-entry rules). Pick: SMA 8/50 + 1% band + 5×ATR(14) trailing stop, re-entry on a new 10-day
    closing high: $242k vs $165k, drawdown 30% vs 56%, 26/26 start dates, 4/6 check sets. Capped stops reached 26%
    drawdown but failed the checks. New: `pinescript/lite_daily_trend_v4.pine`, `backtest/v4_meta.py`,
    `backtest/LITE_backtest_report_V4.html`.
12. **V5: 4H or a two-stage stop to beat V4** (owner chose: same window for all, 6 Dec 2023 → now; stop-loss orders
    only; goal = drawdown below V4 with profit above B&H; peers on 4H as checks). New data
    `backtest/data/2026-11-03-hourly/` (1h + 1d for LITE, COHR, AAOI, CIEN, NVDA), `backtest/backtest_v5.py`
    (4H bars, SMA band / Supertrend / Donchian trends, V4 broker), a two-stage stop type `atr2` added to
    `backtest_v4.py` (V4 results unchanged, verified byte-identical), `backtest/v5_meta.py`,
    `backtest/LITE_backtest_report_V5.html`. Result: no new winner. ~30% drawdown is the floor; daily V4 stays best
    ($253.5k, 30.3%, 4/5 stocks on this window). No V5 Pine script was made because nothing beat V4.
13. **Private repository (pending).** `starter-web` is a fork of the public `scm-ninja/starter-web`, so GitHub
    won't let it be made private. Plan: the owner creates an empty private repository `Dpatelmac/Pine-Research`
    (this session can't create repositories); then push the `LITE-research` branch there as its main branch.

## Open ideas, not done yet

- Test V2 (Percent, 3%/5% trail) on 2–3 other stocks to check whether the improvement is real or over-fitted.
- Lower drawdown below ~30% needs tools the owner hasn't allowed yet: a daily-trend filter for 4H entries,
  volatility/ADX filters, or a QQQ market filter.
- V3: a regime switch (use V3 only when volatility or trend strength is high, otherwise hold) to fix its losses
  on choppy LITE 2016–2023 and on steady risers like NVDA; walk-forward re-optimisation instead of one fixed setting.
- A trend filter used as an *exit* (sell or tighten when price closes below the 200-day average) instead of an entry filter.
- A hybrid: hold the stock most of the time and step aside only on large drops.
- Compare the Python numbers against TradingView's Strategy Tester for one chart once the Pine scripts are compiled.
- Optionally publish the reports (GitHub Pages or private links) so they open in a browser without downloading.
