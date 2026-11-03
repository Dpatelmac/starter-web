# LITE Dip-Rebound Strategy: Findings

All results are simulations of the Pine strategies on Yahoo Finance data (regular hours), with $10,000 start,
100% of equity per trade, 0.1% commission per side, 0 slippage, long and flat only. Signals are taken at bar
close, entries fill at the next bar's open, stops fill at the stop price or at the open on a gap. They are not
TradingView's own Strategy Tester and **not investment advice**. Data as of 3 Nov 2026 (last bar partial).

## Files in this repository

| What | Where |
|---|---|
| Pine strategy V1 (flowchart, Dollar/Percent toggle) | [`pinescript/lite_dip_rebound_two_stage_trail.pine`](../pinescript/lite_dip_rebound_two_stage_trail.pine) |
| Pine strategy V2 (trend filter, 3% tight trail) | [`pinescript/lite_dip_rebound_two_stage_trail_v2.pine`](../pinescript/lite_dip_rebound_two_stage_trail_v2.pine) |
| Report: V1, past 1 month (1D → 2m) | [`backtest/LITE_backtest_report.html`](../backtest/LITE_backtest_report.html) |
| Report: V1, past 6 months (1D/4H/2H/1H) | [`backtest/LITE_backtest_report_6M.html`](../backtest/LITE_backtest_report_6M.html) |
| Report: V1 Dollar vs Percent, 4 years | [`backtest/LITE_backtest_report_4Y.html`](../backtest/LITE_backtest_report_4Y.html) |
| Report: V2 vs V1, 4 years | [`backtest/LITE_backtest_report_V2.html`](../backtest/LITE_backtest_report_V2.html) |
| Pine strategy **V3** (daily trend: SMA 8/45 with a 1% band) | [`pinescript/lite_daily_trend_v3.pine`](../pinescript/lite_daily_trend_v3.pine) |
| Report: **V3** daily trend search, LITE 3 years + 5 test sets | [`backtest/LITE_backtest_report_V3.html`](../backtest/LITE_backtest_report_V3.html) |
| Pine strategy **V4** (V3 trend + 5×ATR trailing stop order) | [`pinescript/lite_daily_trend_v4.pine`](../pinescript/lite_daily_trend_v4.pine) |
| Report: **V4** more profit AND lower drawdown than buy & hold | [`backtest/LITE_backtest_report_V4.html`](../backtest/LITE_backtest_report_V4.html) |
| Report: **V5** 4H and two-stage-stop checks vs V4 (no new winner) | [`backtest/LITE_backtest_report_V5.html`](../backtest/LITE_backtest_report_V5.html) |
| Backtest engines and report builder | [`backtest/`](../backtest/) (see its [README](../backtest/README.md)) |
| Data snapshot the results came from | [`backtest/data/2026-11-03/`](../backtest/data/2026-11-03/) |
| One-command rebuild / fresh data download | [`backtest/rebuild_all.sh`](../backtest/rebuild_all.sh) · [`backtest/fetch_data.sh`](../backtest/fetch_data.sh) |
| Original flowchart | [`docs/flowchart.jpg`](flowchart.jpg) · [`docs/flowchart.md`](flowchart.md) |
| Project context for new Claude sessions | [`CLAUDE.md`](../CLAUDE.md) · [`docs/session_log.md`](session_log.md) |

The reports are self-contained HTML files: download one and open it in any browser, no internet needed.

## The strategy (from the flowchart)

Track the highest price → when price falls a set amount below it (the dip), track the lowest price → buy when
price rebounds 0.5% off that low → wide trailing stop → once price reaches the profit target, swap to a tight
trailing stop → after any sale, start again with a fresh high.

| Setting | Dollar mode (flowchart) | Percent mode | V2 default |
|---|---|---|---|
| Dip from high | $60 | 6% | 6% |
| Rebound from low | 0.5% | 0.5% | 0.5% |
| Wide trailing stop | $95 | 9.5% | 9.5% |
| Profit target | +$60 | +6% | +6% |
| Tight trailing stop | $10 | 1% | **3%** |
| Trend filter (buy only above 200-day average) | — | — | available, off by default |

## 1. Past month (Oct 5 → Nov 3, 2026)

LITE fell from $1,092 to $681 (−37%). Every timeframe lost money but lost less than buy & hold.

| Timeframe | $10k today | Return | Trades | Win rate | Max drawdown |
|---|---|---|---|---|---|
| 1D | $8,656 | −13.4% | 4 | 25% | −18.0% |
| 4H | $8,330 | −16.7% | 4 (+1 open) | 25% | −20.2% |
| 2m | $8,260 | −17.4% | 7 (+1 open) | 43% | −24.2% |
| 5m | $8,164 | −18.4% | 7 (+1 open) | 43% | −24.7% |
| 30m | $7,638 | −23.6% | 7 | 43% | −27.8% |
| 1H | $6,919 | −30.8% | 4 (+1 open) | 0% | −35.0% |
| 15m | $6,796 | −32.0% | 5 | 0% | −35.1% |
| Buy & hold | $6,283 | −37.2% | — | — | — |

## 2. Past 6 months (May 4 → Nov 3, 2026)

LITE went from $987 to $685 (−30%). Only the daily chart made money.

| Timeframe | $10k today | Return | Trades | Win rate | Profit factor | Max drawdown |
|---|---|---|---|---|---|---|
| 1D | $11,277 | +12.8% | 24 | 45.8% | 1.14 | −26.8% |
| 4H | $9,646 | −3.5% | 31 (+1) | 51.6% | 0.97 | −49.1% |
| 2H | $5,238 | −47.6% | 33 (+1) | 42.4% | 0.57 | −58.4% |
| 1H | $4,949 | −50.5% | 32 (+1) | 43.8% | 0.66 | −56.6% |
| Buy & hold | $6,975 | −30.2% | — | — | — | — |

## 3. Four years: Dollar vs Percent mode

Daily over 4 years (Nov 2022 → Nov 2026, LITE $72.70 → $685): Dollar $20,644 (+106%), Percent $21,984 (+120%),
buy & hold **$93,967 (+840%)**. Dollar mode made no trade until Dec 2025 because a $60 dip was impossible while
LITE traded at $38–$110.

Dec 2023 → now (LITE $42.45 → $685): best was 4H Percent at $44,384 (+344%); buy & hold **$161,147 (+1,512%)**.

## 4. V2: trend filter and wider tight trail

Value of $10,000 today (★ = best per column):

| Version | 1D · 4 years | 4H · Dec 2023 → now | 2H · Dec 2023 → now | 1H · Dec 2023 → now |
|---|---|---|---|---|
| V1 · Dollar (original) | $20,644 | $20,817 | $10,477 | $7,604 |
| V1 · Percent, 1% trail | ★ $21,708 | $44,384 | $22,159 | $15,735 |
| V2 · Trend filter, 1% trail | $13,589 | $22,754 | $14,922 | $9,073 |
| **V2 · 3% trail** | $20,874 | ★ **$67,813** | $32,761 | ★ $23,311 |
| V2 · 5% trail | $13,140 | $43,635 | ★ $63,100 | $23,034 |
| V2 · Trend filter + 3% trail | $11,735 | $40,403 | $24,172 | $15,542 |
| V2 · Trend filter + 5% trail | $9,886 | $24,914 | $35,653 | $15,836 |
| Buy & hold | $92,746 | $161,147 | $161,147 | $161,147 |

**Wider tight trail (3–5%) helps on intraday charts.** With a 1% trail, winners were sold too early. 4H improved
from $44k to $68k with a 3% trail; 2H from $22k to $63k with a 5% trail; 1H from $16k to $23k. On the daily
chart it made no real difference (3%) or hurt (5%).

**The 200-day trend filter hurt on LITE.** It lowered profit in almost every test. In 2022–2023 LITE moved
sideways below its average; V1 had made small profits on those dips, and the filter blocked them, which also
meant less compounding later. It reduced some drawdowns a little, not enough to pay for the lost profit.
That is why it ships switched off in the V2 script.

## 5. V3: a daily-chart strategy that beats buy & hold on LITE (last 3 years)

Goal: long/flat on the 1D chart, beat buy & hold over 3 Nov 2023 → 3 Nov 2026 (buy & hold: $10k → **$164,604**,
max drawdown 56%). Same rules: signals at the close, fills at the next open, 0.1% commission, 100% of equity.

**Search.** 412 settings across 11 trend-following families (SMA/EMA crosses, SMA cross with a band, close above
SMA/EMA, Donchian breakout, Supertrend, ROC momentum, MACD, trailing % stop, Chandelier ATR stop). Only the SMA-cross
families beat buy & hold (18 of 130 plain crosses; 33 of 80 with a band). None of the others did.

**Pick: V3 = SMA 8 / SMA 45 with a 1% band.** Buy when the 8-day SMA closes more than 1% above the 45-day SMA; sell
when it closes more than 1% below it.

| | V3 | Buy & hold |
|---|---|---|
| $10k → (3 years) | **$213,237** (+2,032%) | $164,604 (+1,546%) |
| Yearly growth (CAGR) | 177% | 154% |
| Max drawdown | **40%** | 56% |
| Trades / win rate / time in market | 5 / 60% / 72% | 1 / — / 100% |
| Position today | flat (sold 21 Oct 2026 at $863) | holding (~$680) |

Its five trades: Nov 2023 → Feb 2024 (+10%), May → Aug 2024 (−12%), Aug 2024 → Feb 2025 (+54%, then sat out the
early-2025 crash of about 50%), **May 2025 → Jun 2026 (+1,358%, $66 → $966)**, Aug → Oct 2026 (−4%, then sat out the
fall to $680).

**Why trust it a little:** the good zone is broad (fast 8–15 × slow 45–55 × band 1–2% mostly beat buy & hold), and
from every one of 26 monthly start dates (May 2023 → Jun 2025, held to today) V3 beat buy & hold, e.g. starting
1 Jan 2025: $142k vs $80k.

**Why not trust it too much:**

| Test set | V3 ÷ buy & hold |
|---|---|
| LITE · 3 yrs (where it was picked) | ✓ 1.30× |
| LITE · 2016–2023 (choppy) | ✕ 0.39×: V3 lost 28% while buy & hold made 86% |
| COHR · 3 yrs | ✓ 1.01× |
| AAOI · 3 yrs | ✓ 1.11× |
| CIEN · 3 yrs | ✓ 1.12× |
| NVDA · 3 yrs (steady riser) | ✕ 0.50× |

It wins in trending markets with deep crashes and loses in choppy markets or steady climbs. Almost all of its LITE
profit came from one trade, and there are only five trades, so the edge rests on a small sample.

## 6. V4: more profit AND a much lower drawdown than buy & hold

Owner's brief: profit above buy & hold and a much lower max drawdown (intrabar, TradingView style), checked beyond
LITE; the new tool allowed is a real stop-loss order. Search: 7,050 settings (trend SMA fast × slow × band, 23 stop
orders, 3 re-entry rules) on LITE 3 years; 283 beat buy & hold on both. Then all were run on the five check sets.

**Pick: V4 = SMA 8/50 with a 1% band + a trailing stop order 5 × ATR(14) below the highest high since entry;**
after a stop-out it buys again only on a close above the prior 10-day closing high (or on a fresh trend up-turn).

| LITE · 3 Nov 2023 → 3 Nov 2026 | V4 | V3 | Buy & hold |
|---|---|---|---|
| $10k → | **$242,034** | $213,237 | $164,604 |
| Max drawdown (intrabar) | **30.3%** | 39.9% | 56.1% |
| Trades / win rate | 5 / 80% | 5 / 60% | — |

- From all **26 monthly start dates** (May 2023 → Jun 2025, held to today) V4 beat buy & hold on **both** profit and
  drawdown; its worst drop was always about 30% (buy & hold 45–56%).
- On the checks it beat buy & hold on both in **4 of 6** sets (LITE 3y, COHR, AAOI, CIEN) and lost on LITE 2016–2023 and
  NVDA, the same pattern as V3 but with smaller drops everywhere.
- **Tight stops don't work on LITE:** 10–25% trailing or 2–3×ATR stops sell too often and miss the 2025–26 run.
- **Below ~30% drawdown it stops being robust:** capping the stop (e.g. "5×ATR, never more than 22%") reaches 26% on
  LITE but beats buy & hold in only 1 of 6 sets. It is a fit to LITE's exact path, so it was not picked.

## 7. V5: can a 4H chart or a two-stage stop beat V4? (No)

Owner's brief: try 4H, or any strategy, for profit above buy & hold and a drawdown below V4's; tools limited to trend
rules plus stop-loss orders; everything on the same window, **6 Dec 2023 → 3 Nov 2026** (hourly data starts there);
checked on COHR, AAOI, CIEN and NVDA 4H/1D. On this window buy & hold on LITE: $159,852, drawdown 56.1%.

| LITE · 6 Dec 2023 → 3 Nov 2026 | Value | Max drawdown | Beats B&H on both, of 5 stocks |
|---|---|---|---|
| **V4 daily** (SMA 8/50 band + 5×ATR) | **$253,507** | **30.3%** | **4/5** (fails NVDA) |
| Best 4H (SMA 16/100 band + 8×ATR) | $191,184 | 30.6% | 3/5 (fails COHR, NVDA) |
| Lowest-drawdown 4H (SMA 8/80 2% + 6×ATR) | $161,103 | 30.0% | 1/5 |
| Daily two-stage stop (5×ATR → 1.5×ATR after +50%) | $157,989 | 29.9% | 0/5 (just under B&H profit on LITE) |
| Buy & hold | $159,852 | 56.1% | — |

- Searched 5,203 4H settings (SMA band, Supertrend, Donchian × 15 stops × 3 re-entry rules), 15,480 4H and 12,900
  daily two-stage-stop settings. **No setting had a drawdown below 30% and profit above buy & hold.**
- 4H adds noise: more stop-outs and lower profit; its longer averages also need ~5 months of hourly data to warm up.
- The ~30% floor is LITE's October 2026 fall. Exiting it earlier needs a tighter stop, and tighter stops sell too
  early in the 2025–26 run. Going lower would need other tools (daily-trend or volatility filters, a market filter)
  or accepting less profit.

## Conclusion in simple words

- Over the long run the strategy made money (about 2× in 4 years, up to about 6.8× for V2 on 4H), but
  **buying and holding LITE made far more** (about 9–16×). In a stock running straight up, stepping in and out
  keeps getting you off the train.
- The fixed dollar amounts break when the share price changes a lot; **Percent mode is the better design**.
- **Best tested setup: V2, Percent mode, 3% tight trail on the 4H chart** (or 5% on 2H). It still had drawdowns
  of 35–55% from peak, which are hard to sit through.
- In falling periods (last month, last 6 months) the strategy lost less than holding.
- These settings were chosen on one exceptional stock, so they are likely over-fitted. Test them on other stocks
  before trusting them.
- **V3 (daily SMA 8/45 with a 1% band) is the first strategy that beat buy & hold on LITE**, over the last 3 years:
  $213k vs $165k with a smaller drawdown (40% vs 56%), mainly by stepping aside in the early-2025 and Oct-2026
  crashes. It is not a sure thing: it lost to buy & hold on LITE 2016–2023 and on NVDA.
- **V4 adds a wide 5×ATR stop-loss order to V3:** $242k vs $165k, max drawdown **30% vs 56%**, better than buy & hold on
  both from every start date tested. Getting the drawdown much below 30% only worked by fitting LITE's exact history.
- **4H and two-stage stops (V5) did not beat V4**: with trend rules + stop orders only, ~30% drawdown is the floor on
  LITE while keeping profit above buy & hold. Daily V4 remains the best strategy found.

## Why LITE flew in 2025–2026 (brief)

| When | Price (approx.) | What changed |
|---|---|---|
| 2022 – mid 2025 | $40–75 | Sideways, slow telecom business |
| Jul 2025 | ~$110 | AI demand starts showing in results |
| Oct 2025 | ~$194 | Rally speeds up |
| Jan 2026 | ~$385 | About 4–5× for 2025 |
| Apr 2026 | ~$858 | Momentum and index buying |
| Oct 2026 | ~$1,100+ | Peak |
| Nov 2026 | ~$685 | About a 37% fall in one month |

1. **Its parts became an AI bottleneck.** AI data centers move huge amounts of data between GPUs over fast
   optical links (800G, next 1.6T). Lumentum makes key laser chips (EMLs) for them, with a reported 50–60%
   market share, and analysts said demand was outrunning supply.
2. **Results confirmed it.** Revenue roughly doubled year over year; about 60% of revenue was tied to cloud and
   AI by late 2025, according to the CEO; earnings kept beating estimates and price targets kept rising.
3. **New products added long-term hope.** Reported co-packaged optics wins (commitments said to exceed
   $5 billion) and a third hyperscale customer for its optical circuit switches.
4. **Momentum and index buying.** Lumentum was set to join the Nasdaq-100 in May 2026, and "AI winner" headlines
   drew in momentum traders.

The recent fall has no single clear cause in the sources found; likely profit-taking, valuation worries and
nerves ahead of earnings (reportedly around 5 Nov 2026). Claims found in only one source, such as reported
acquisition talks or a large Nvidia investment, are left out as unconfirmed. The sources are mostly news and
investor-commentary articles whose numbers and dates sometimes conflict.

Sources:
[Tiger Brokers – Nasdaq-100 inclusion](https://www.itiger.com/news/1105822165) ·
[Motley Fool](https://www.fool.com/investing/2025/08/21/up-49-in-3-months-this-magnificent-ai-stock-can) ·
[Zacks via TradingView](https://www.tradingview.com/news/zacks%3A0d94cecd4094b%3A0-lite-stock-jumps-219-in-a-year-will-the-momentum-continue-in-fy26) ·
[Barchart](https://business.minstercommunitypost.com/minstercommunitypost/article/barchart-2025-11-27-insatiable-demand-is-powering-this-picks-and-shovels-ai-stock-up-245-should-you-buy-it-here) ·
[PredictStreet](https://business.mammothtimes.com/mammothtimes/article/predictstreet-2025-12-16-lumentum-holdings-inc-lite-illuminating-the-future-of-ai-and-optical-networking) ·
[TechNews](https://technews.tw/2025/12/26/lumentum-stock-on-track-to-record-8th-consecutive-monthly-gain/) ·
[Nasdaq](https://www.nasdaq.com/articles/lumentum-stock-rides-strong-ai-push-sign-more-upside) ·
[GuruFocus](https://www.gurufocus.com/news/9165751/lumentum-stock-gains-after-5-billion-copackaged-optics-win) ·
[Yahoo Finance](https://finance.yahoo.com/markets/stocks/articles/lumentum-lite-beats-q1-earnings-152003979.html) ·
[Investing.com](https://www.investing.com/news/analyst-ratings/lumentum-stock-named-top-ai-optics-pick-by-b-riley-on-capacity-93CH-4990489) ·
[24/7 Wall St (Oct 19)](https://247wallst.com/investing/2026/10/19/optics-stocks-rally-ahead-of-earnings-applied-optoelectronics-jumps-5-lumentum-adds-4-coherent-rises-2/) ·
[24/7 Wall St (Oct 28)](https://247wallst.com/investing/2026/10/28/optical-stocks-climb-as-analysts-flag-ai-bottleneck-lumentum-rises-4-applied-optoelectronics-and-corning-gain-3-coherent-sits-out-the-rally/)
