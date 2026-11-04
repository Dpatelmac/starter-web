# Trading research summary

Session dates: 2026-11-01 to 2026-11-04. Branch: `pullback_research`. Market data through the close of
2026-10-30. Research only, not financial advice. **No trades were sent.**

## Bottom line

- Six strategy ideas were tested on US stocks (2005 to Oct 2026), with
  trading costs and out-of-sample checks; four were pre-registered (rules and
  pass marks committed to git before running). **None passed.**
- Short-term price patterns after drops have no tradable edge at retail costs.
- **Current recommendation: hold, no new trades; keep idle cash earning the
  T-bill rate.**
- Best risk-adjusted lead, not yet verified: SPY with a 200-day switch (hold
  T-bills when SPY is below its 200-day average). It needs its own
  pre-registered test before it is recommended.

## Ranking (like-for-like)

All strategies measured the same way: 2005-01-03 to 2026-10-30, 5 bps per
side, before tax, cash earning T-bills, metrics from daily values
(`report/compare.py` -> `report/results/compare.csv`). Ranked by Sharpe.

| Rank | Strategy | Yearly return | Sharpe | Worst fall | Months positive | Winning trades | $1 grew to |
|---|---|---|---|---|---|---|---|
| 1 | Lead: SPY with 200-day switch (not yet pre-registered) | 9.5% | 0.65 | -24% | 72% |  | $7.24 |
| 2 | 4. Weekly pullback portfolio (top 20, buffer) | 14.2% | 0.55 | -64% | 64% |  | $18.21 |
| – | Benchmark: SPY buy & hold | 10.8% | 0.54 | -55% | 66% |  | $9.33 |
| – | Benchmark: 50/50 SPY / T-bills | 6.7% | 0.54 | -31% | 69% |  | $4.08 |
| 3 | 5a. Plain top-20 momentum (no risk controls) | 11.7% | 0.47 | -56% | 59% |  | $11.08 |
| 4 | 3. Weekly pullback, daily entries (5-day hold) | 8.7% | 0.43 | -53% | 59% | 53.7% | $6.19 |
| 5 | 5. Regime-gated momentum (full strategy D) | 7.1% | 0.43 | -32% | 66% |  | $4.46 |
| 6 | 6. Put-write layer (CBOE PutWrite index) | 6.9% | 0.38 | -37% | 74% |  | $4.27 |
| 7 | 2. Oversold in a selloff (holdout rule, 3-day) | 3.2% | 0.19 | -30% | 46% | 57.8% | $1.99 |
| 8 | 1. Buy every 2% drop (3-day hold) | 0.9% | 0.06 | -56% | 51% | 52.1% | $1.22 |

No strategy wins on profit, win rate and drawdown at once. The weekly
pullback portfolio has the most profit but a -64% worst fall, and it failed on
stocks outside the S&P 500/400 (0.7% a year there). Missing bankrupt and
acquired stocks flatter the stock-picking strategies.

## The six tests

| # | Idea | Folder | Pre-registered | Verdict |
|---|---|---|---|---|
| 1 | Buy S&P 500/400 stocks after a 2%+ drop on 1M+ volume | `dip_rebound/backtest.py` | no | No edge: 3-day edge vs same-morning stocks +0.02%, t 0.78 |
| 2 | Oversold stock (down 5%+ prior week) on an S&P down 1%+ day, on 835 new stocks | `dip_rebound/holdout.py` | yes | Failed: t 0.56, negative in 2005-15 |
| 3 | 510 drop measures, cutoffs, holds and volume filters | `dip_rebound/sweep.py`, `pullback_check.py` | robust test fixed in code | 0 robust; multi-day pullbacks bounce ~0.09%/trade, about the cost |
| 4 | Weekly top-N pullback portfolio, 36 versions | `dip_rebound/weekly.py` | yes | Failed: 0 of 36; 50-97x yearly turnover |
| 5 | Regime-gated, risk-budgeted 12-1 momentum | `momentum_regime/momentum.py` | yes | Failed: lower Sharpe than SPY in 2 of 3 samples |
| 6 | Cash-secured put-write layer on idle cash (^PUT) | `putwrite/putwrite.py` | yes | Failed after 2007 (after costs and tax); account too small for one SPY put |
| 8 | Top 4 of the 10 biggest S&P 500 decliners, trailing-stop exits (3%; 5/8%/ATR reported) | `top4_trailing/top4.py` | yes | Failed: 3% stop makes -0.9% to 3.4% a year (low drawdown only from low exposure); wider stops track the market, ranking barely beats random |
| 7 | User's pullback framework v6: ignore list + bounce signals + final flush | `pullback_v6/v6.py` | yes | Failed: no rule passes; only the final-flush signal is positive in all samples, weak since 2016 |

Details, tables and caveats are in each folder's `README.md` and
`PREREGISTRATION.md`.

## Paper portfolio snapshot (close of 2026-10-30)

SIGNUM bot "IBKR Paper - Trend Radar (TR-GC-Stocks-4)" (id 28473), Interactive
Brokers paper account. NAV $23,941; cash $15,282 (64%). Stock sleeve: 63%
chips/tech, beta 2.15 vs SPY, 34% annualized volatility. **The bot logged no
activity after 2026-10-14.**

| Stock | Shares | Close | Value | Share of NAV | Vs 200-day avg |
|---|---|---|---|---|---|
| ISRG | 3 | $432.01 | $1,296 | 5.4% | -0.2% |
| PG | 8 | $161.57 | $1,293 | 5.4% | +10.0% |
| ADI | 3 | $417.11 | $1,251 | 5.2% | +12.5% |
| QCOM | 6 | $164.79 | $989 | 4.1% | -2.1% |
| MU | 1 | $884.74 | $885 | 3.7% | +18.5% |
| ARM | 4 | $205.97 | $824 | 3.4% | -10.0% |
| INTC | 10 | $65.76 | $658 | 2.7% | -24.3% |
| STX | 1 | $644.58 | $645 | 2.7% | -6.8% |
| META | 1 | $614.99 | $615 | 2.6% | -2.6% |
| NVDA | 1 | $204.64 | $205 | 0.9% | +0.3% |

Market (computed): SPY 4.1% above its 200-day average, 3% below its high;
XLK -9.3% in October; VIX 19.4; 57% of S&P 500/400 stocks above their 200-day
average; 13-week T-bill 3.97%.

Reported in the news (not computed): Fed held at 3.75-4.00% on 2026-10-28
with two dissents for a hike; futures priced ~83% odds of a hike on
2026-12-09; S&P 500 forward P/E ~18.7 (FactSet); Nasdaq -5% in October on
AI-spending worries.

## Live ledgers: top 4 unexplained S&P 500 losers (illustrations, not tests)

Each day: S&P 500 losers down 2%+ (close >= $20, volume >= 1M); skip
"explained" ones (earnings that day or the evening before, or an 8%+ gap down
at the open); buy the 4 biggest remaining at the next open, $1,000 each; exit
only by trailing stop. Not pre-registered; analyst news not checked; no trades
sent. Prices and earnings dates: Yahoo Finance.

**2 weeks** (drop days 2026-10-21 to 11-03, marked at the 11-04 close;
`top4_trailing/live_2wk/LEDGER.md`), first-10-then-remove selection:
3% stop +$583 on 29 trades (48% profitable); 8% stop +$978 (59%). Without the
trades held through earnings: +$107 and +$11.

**3 months** (drop days 2026-08-06 to 11-03, 63 days; interactive report
`top4_trailing/live_3m/report.html`):

| Selection, 8% stop | Trades | Total P&L | Closed trades | Open positions | Win rate | Worst drawdown |
|---|---|---|---|---|---|---|
| First 10, then remove explained | 239 | +$2,010 | -$4,575 | +$6,585 | 40% | -$2,709 |
| **Top 4 after removing explained** | 252 | **+$3,526** | -$3,361 | +$6,887 | 40% | -$2,465 |
| Same + skip stocks reporting within 10 days | 247 | +$3,004 | -$3,365 | +$6,369 | 41% | -$2,608 |

The 3% stop loses money in every version (-$169 to -$754). The whole gain is
in positions still open; closed trades lost money (about 26% of closed trades
profitable). Up to 60 positions were open at once (~$60,000). SPY over the same
window: -0.3%. APP was caught by the new selection (bought 2026-11-02 at
$234.52, +15.8% at the 11-04 close; +24% after hours on its earnings report,
not counted). Missing price data: NTAP.

## Open items

1. Check why the SIGNUM bot has been inactive since 2026-10-14.
2. Review the chip/tech concentration (beta 2.15) going into chip earnings
   and a likely December hike.
3. Confirm the idle cash earns the T-bill rate (or hold a T-bill fund).
4. Next candidate test: SPY with a 200-day switch, pre-registered, on S&P
   history before 2005 plus QQQ, small caps and international indexes.
5. Measure the evening prompt's value: log nightly composite scores and
   compare next-day returns of high vs low scores with the same edge measure.
6. Before trading the top-4 ledger rule: pre-register and backtest "top 4
   after removing explained" with an 8% stop over 20 years, and test a
   position cap (20-24 for a ~$24k account), a per-sector limit, a cool-off
   after a stop-out, and skipping stocks that report during the hold.
7. Build the nightly paper log: top losers + AI ranking of the top 4, with
   next-day opens and trailing-stop exits, to judge the AI step after 2-3 months.
8. Delete the old branch `claude/blissful-euler-i26lau` on GitHub (the session
   couldn't; work now lives on `pullback_research`).
9. Copy `research/` to the local research home
   `/Users/claud/Documents/1Projects/tradingbot2/research` (Remote Control
   was not connected, so a cloud session could not write there).

## Deliverables

- Offline report (no internet needed): `research/report/trading-research.html`
  (rebuild: `python3 research/report/build_report.py`).
- Online dashboard (Claude artifact, private until shared):
  https://claude.ai/artifact/3AtkyTudQyCmEdXpCk7MSQ
  (page source: `research/report/dashboard/index.html`).
- Evening prompt review: `research/evening_prompt_review.md`.
- 3-month ledger report (offline, interactive):
  `research/top4_trailing/live_3m/report.html` (rebuild: `python3 ledger3m.py`
  then `python3 build_report.py` in that folder).
- 2-week ledger: `research/top4_trailing/live_2wk/LEDGER.md`.
- Git branch: `pullback_research` (renamed from `claude/blissful-euler-i26lau`).

## Reproduce

```bash
pip install yfinance pandas numpy pyarrow lxml requests matplotlib
python3 research/dip_rebound/fetch_data.py      # prices (~2 min), not committed
python3 research/dip_rebound/backtest.py
python3 research/dip_rebound/holdout.py         # downloads the 835 holdout stocks
python3 research/dip_rebound/sweep.py
python3 research/dip_rebound/pullback_check.py
python3 research/dip_rebound/weekly.py
python3 research/momentum_regime/snapshot.py    # also saves ^IRX T-bill yields
python3 research/momentum_regime/momentum.py
python3 research/putwrite/putwrite.py
python3 research/report/compare.py
python3 research/report/build_report.py
```

## Method rules and assumptions

- Signals judged against stocks bought the same morning (removes market moves).
- Buy at the next open after a signal; costs on traded value, 5 bps per side
  base (commission-free market orders), 10 bps stress.
- Out-of-sample: 2005-15 vs 2016-26, plus 835 stocks outside the S&P 500/400.
- Put-write test assumptions: 0.5%/yr trading drag; taxes 32% ordinary income,
  15% dividends and long-term gains, 21.8% Section 1256 option profits.
- Data: Yahoo Finance (prices, ^PUT, ^VIX, ^IRX), Wikipedia (index members),
  Nasdaq screener (holdout list), SIGNUM (portfolio). Delisted stocks missing.
