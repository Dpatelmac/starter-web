# Online dashboard page source

`index.html` is the page stored in the Claude Dashboard artifact
https://claude.ai/artifact/3AtkyTudQyCmEdXpCk7MSQ (store document
`files/index.html`). It runs only inside that artifact: it reads datasets
through the artifact's `dash` API, not from local files.

Datasets in the artifact (uploaded copies of `research/dip_rebound/results/dashboard/`):
headline, rules, portfolio, curves, holdout, sweep, pullback, weekly,
weekly_spy (all CSV, fixed). Computed in the page: sweep_summary,
weekly_summary, weekly_by_sample.

For an offline version use `research/report/trading-research.html`.
