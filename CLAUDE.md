# CLAUDE.md: LITE strategy research (branch `LITE-research`)

This branch holds a TradingView Pine Script strategy built from a flowchart, its backtests on Lumentum (NASDAQ:
LITE), and offline interactive HTML reports. `master` is an unrelated static-site starter and must stay
untouched: **do not merge this branch into `master`** unless the owner asks.

Start here:
1. `docs/LITE_strategy_findings.md`: every result table, the conclusion and why LITE rallied.
2. `docs/session_log.md`: what was asked and done, in order, and the open ideas.
3. `backtest/README.md`: how to re-run everything.

## The owner's standing rules for Pine Script (apply to every strategy in this repo)

- Pine Script **v6**. Convert indicator-only code to strategy code; nothing a TradingView strategy can't run.
- Preserve any timeframe logic; define timeframes and gaps explicitly so the meaning is unchanged. Fill gaps.
- Plot what the indicator plotted so the visuals are preserved.
- **Long and flat only**; never open a short.
- **100% of equity** per trade: `default_qty_type=strategy.percent_of_equity, default_qty_value=100`.
- **Commission 0.1%**: `commission_type=strategy.commission.percent, commission_value=0.1`. **Slippage 0**: `slippage=0`.
  `strategy.commission.percent` / `strategy.slippage` are *not* variables; set these only inside `strategy()`.
- Write the `strategy(...)` call **on one line** (line breaks there caused compiler errors).
- Leave every other strategy setting at its default (don't set it).
- **Never use `lookahead_on`.**
- **Start Date / End Date inputs**, defaults 1 Jan 2018 and 31 Dec 2069; trade only inside them.
- Strategy title starts with **`Demo GPT - `**.

## Files

| Path | What |
|---|---|
| `docs/flowchart.jpg`, `docs/flowchart.md` | The original flowchart and a text version |
| `pinescript/lite_dip_rebound_two_stage_trail.pine` | V1: flowchart strategy + "Amounts in" Dollar (default) / Percent toggle |
| `pinescript/lite_dip_rebound_two_stage_trail_v2.pine` | V2: Percent default, 3% tight trail, optional 200-day trend filter (off) |
| `backtest/backtest.py` | Python replica of V1 with TradingView-style fills |
| `backtest/backtest_v2.py` | Same engine plus V2 options (trend filter, tight-trail override) |
| `backtest/build_report.py` + `report_template.html` | Builds the self-contained, offline HTML reports |
| `backtest/rebuild_all.sh` | One command: all backtests + all four reports (byte-identical to the committed ones) |
| `backtest/fetch_data.sh` | Downloads a fresh Yahoo snapshot (never overwrites an existing one) |
| `backtest/data/2026-11-03/` | The exact data the committed results came from (1m, 6m, 4y, v2 sets) |
| `backtest/tools/check_report.js` | Playwright smoke test of every report (errors, overflow, screenshots) |
| `backtest/LITE_backtest_report*.html` | 1-month, 6-month, 4-year and V2 reports |

## How the simulator matches the Pine strategy (keep these in sync)

- Signals are computed at **bar close**; a market entry fills at the **next bar's open**.
- One exit order whose stop is replaced every bar; it fills at the stop, or at the **open if the bar gaps through it**.
- Quantity = `floor(equity / close at the signal bar)`; commission 0.1% each side; no slippage.
- State machine: 0 = flat, tracking the high → 1 = dip found, tracking the low → 2 = long with the wide trail,
  watching the target → 3 = long with the tight trail. After every sale: back to 0 with the high reset to that
  bar's close. Outside the date range: no entries; an open position is closed.
- Max drawdown is intrabar (uses bar highs and lows while long); the drawdown chart is at bar close.
- 4H/2H bars are built from 1H bars on TradingView's session split for US stocks (anchored 09:30:
  4H = 09:30–13:30, 13:30–16:00).
- V2 trend filter: average of the **previous 200 completed daily closes** (Pine builds it in an array from
  `close[1]` on each new day, with no `request.security` and no lookahead; Python uses official daily closes).
  Below the average, the strategy stays in state 1 and buys on the first bar that qualifies.
- Results are simulations, not TradingView's Strategy Tester; expect small differences. Pine has never been
  compiled in this environment, so the owner compiles it in TradingView.

## Data facts that shape every test

- Source: Yahoo Finance chart API (`query1.finance.yahoo.com/v8/finance/chart/LITE`), regular hours,
  browser-like User-Agent. **Limits: 1h ≈ last 730 days, 30m/15m/5m/2m last 60 days, 1m last 7 days.**
  That is why the 4-year test is daily-only and intraday covers Dec 2023 → now.
- LITE traded at $38–$110 from 2022 to mid-2025, then ran to about $1,100 (Oct 2026), and was about $685 on
  3 Nov 2026. Fixed-dollar distances ($60 dip, $95 stop) don't work across that range, which is why Percent
  mode exists (6% / 0.5% / 9.5% / +6% / 1%, the same proportions at ~$1,000).

## Headline results (details in `docs/LITE_strategy_findings.md`)

- Every version made less than buy & hold over 4 years (strategy ≈ 2–7×, buy & hold ≈ 9–16×).
- Best tested: **V2 Percent, 3% tight trail, 4H**: $10k → $67.8k since Dec 2023 (buy & hold $161k).
  On 2H, a 5% trail was best ($63.1k).
- The 200-day trend filter **lowered** returns in almost every test on LITE.
- In falling periods (last month, last 6 months) the strategy lost less than holding.
- Treat the "best" settings as likely over-fitted to one exceptional stock.

## Report template conventions

- Single HTML file, no external libraries or fonts, works offline. Light/dark tokens on `:root`
  (+ `data-theme` toggle). Categorical colors are fixed slots `--s1..--s8`, assigned in scenario order and never
  cycled; the palette was checked with a colorblind-safety validator.
- `build_report.py` takes several result files; each becomes a switchable window. `REPORT_META` (JSON env)
  sets the title, a version note and a `baseline` scenario for the "vs" column.
- Price and equity charts switch to log scale automatically when the range is wider than 4×.
- After changing the template, run `bash backtest/rebuild_all.sh` and `node backtest/tools/check_report.js`.

## Working conventions

- Use a dated folder under `backtest/data/` for new data; never overwrite the 2026-11-03 snapshot.
- Name new strategy versions `..._v3.pine` etc. with matching `backtest_v3.py` / `LITE_backtest_report_V3.html`,
  and keep older versions unchanged so results stay comparable.
- Not investment advice; say so in reports.
