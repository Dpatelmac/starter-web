# Put-write layer on idle cash (pre-registered test 4)

Rules and pass criteria were committed in `PREREGISTRATION.md` (ba50253)
before any put-write returns were computed. Run: `python putwrite.py`.

## Result: FAIL, so keep the idle cash in T-bills

After-tax figures use base cost (labelled assumptions: 0.5% a year trading
drag; taxes 32% ordinary income, 15% dividends and long-term gains, 21.8% for
Section 1256 option profits). Index and ETF prices are verified data (Yahoo
Finance: ^PUT, SPY, ^IRX, ^VIX, ^GSPC, XYLD).

| Period | Put-write after tax: CAGR / Sharpe / max fall | SPY | 50/50 SPY/T-bills |
|---|---|---|---|
| 1996-07 to 2007-06 (before launch) | 7.5% / **0.54** / -32% | 8.4% / 0.51 / -45% | 5.6% / 0.45 / -23% |
| 2007-07 to 2026-10 (after launch) | 5.0% / 0.42 / -33% | 9.7% / **0.67** / -51% | 5.4% / 0.60 / -28% |

It passes all four criteria before the index launched and fails two after
(Sharpe below both SPY and the 50/50 mix). The 2020-2026 period alone shows
the same pattern (put-write Sharpe 0.51 vs SPY 0.79 and 50/50 0.69).

Context (verified):

- The thesis itself still holds: VIX exceeded the S&P 500's realized
  volatility over the next 21 days on 81-86% of days in every period, by 3.3
  to 4.4 volatility points on average. The premium exists, but after costs and
  annual taxation it has not paid better per unit of risk than simply holding
  less stock.
- The 200-day filter looked excellent before 2007 (Sharpe 0.73 after tax,
  -13% max fall) and was the worst version afterwards (0.36). A good example
  of an in-sample illusion.
- Taxes matter: put-write profits are taxed every year, while SPY's gains are
  deferred until sale. Before tax the post-2007 Sharpe gap is 0.52 vs 0.66; after
  tax 0.42 vs 0.67.
- Right now VIX (19.4) is well above the past month's realized volatility
  (11.8), so option premiums are richer than usual. That's a fact about today,
  not evidence the strategy will work.

## Implementation problem found after pre-registration

One SPY or XSP put needs about $75,600 of collateral (100 x $755.72). The
planned $12,000 layer can't sell a single fully cash-secured contract. The only
liquid fund alternative found, XYLD (S&P 500 buy-write, from 2013), returned
8.2% a year with Sharpe 0.59 before tax, vs SPY 14.2% and 0.85 over the same
period, and its distributions are mostly taxed as ordinary income. This
reinforces the fail verdict.

## Recommendation (for review, no trades)

Keep the idle cash in T-bills or a T-bill fund rather than adding an
option-income layer. Make sure the cash actually earns the ~4% T-bill rate.
