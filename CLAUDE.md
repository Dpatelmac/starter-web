# Notes for Claude

## Research home

The user's local home directory for the trading research and report is:

    /Users/claud/Documents/1Projects/tradingbot2/research

Keep `research/` in this repository mirroring that folder (same layout), and
treat the local path as the default location for research files and the
offline report (`research/report/trading-research.html`). A cloud session
can't write to it directly: either connect the folder through Remote Control
or push to git and let the user copy it.

## Layout

- `research/dip_rebound/`: dip-buying studies (tests 1-4), price data fetcher
- `research/momentum_regime/`: portfolio snapshot, momentum test (test 5)
- `research/putwrite/`: put-write layer test (test 6)
- `research/pullback_v6/`: user's pullback framework, ignore list + signals (test 7)
- `research/top4_trailing/`: top 4 of 10 biggest decliners, trailing-stop exits (test 8);
  `live_2wk/` 2-week ledger, `live_3m/` 3-month ledger, `live_1y/` 1-year test of 32
  versions; `backtest_6y/` 6-year pre-registered test of the top 3 (test 9);
  each with an interactive `report.html`
- `research/report/`: `build_report.py` -> offline `trading-research.html`;
  `compare.py` -> like-for-like ranking; `dashboard/` = online artifact page source
- `research/SUMMARY.md`: findings, ranking, portfolio snapshot, open items
- `research/evening_prompt_review.md`: review of the evening scoring prompt

Price data (`research/dip_rebound/data/`) is not committed; rebuild with
`python3 research/dip_rebound/fetch_data.py`, then `holdout.py` and
`momentum_regime/snapshot.py`.

## Git

Work branch: `pullback_research` (renamed from `claude/blissful-euler-i26lau`;
the old remote branch still needs deleting on GitHub).

## Research rules used so far

- Pre-register rules and pass criteria (commit before running a test).
- Judge signals against same-day stocks, include costs (5 bps per side base),
  test out of sample, label assumptions, never invent data.
- Present proposals for review; never send trades without explicit approval.
