# Review of the "evening decliners" scoring prompt

The prompt asks an AI, after the US close, to score how likely each stock that
fell 2%+ on 1M+ volume (cap > $2B, price > $20) is to rise in the next 1-3
sessions. Stocks come in batches of 10 with per-ticker context (sector, %
change, close, after-hours move, earnings date), app-fetched company facts and
market context (futures, VIX, rates, FX, commodities, Asia/Europe, sector
ETFs). It returns one markdown table with 8 factor scores, a weighted
composite, gap risk, catalysts and sources.

## What it does well

- Explains the purpose of each input (price as an identity fingerprint, %
  change to calibrate search effort, after-hours move as a news flag).
- Blocks common AI shortcuts: copying rows between tickers, treating "no news"
  as bullish, calling a timing difference a "data mismatch" (gives a
  prior-close reconciliation formula).
- Requires 2 sources per ticker, specific peer % moves, and a Low/Medium/High
  gap-risk call; output is machine-parseable.

## Problems found

1. **Composite range is -1 to 9, not 0 to 10.** Positive weights sum to 0.90
   and hidden risk subtracts 0.10, so all-neutral (5s) scores 4.0, not 5.
2. **Hidden Risk scale is inverted** (higher = riskier) but shares the generic
   "8-10 = positive signal" anchors, inviting mis-scoring.
3. **AI Confidence is weighted into the direction score** (0.15). It measures
   research quality, not likely direction, so well-sourced bad news gets a
   boost. Better as a filter or flag.
4. **Wrong sectors in the sample:** FN (Fabrinet) and CIEN (Ciena) are optical
   networking (tech), not Utilities; XLU was flagged as their relevant sector.
5. **Stale "next/last" earnings date:** CIEN showed 2026-09-03 (past).
   Separate next and last dates.
6. **SEC lookups failed for every ticker** in the sample run.
7. **Batch scores aren't comparable** if batches are grouped by sector.

## What the backtests say about its premise

Price data alone gives the prompt nothing to build on (see `SUMMARY.md`):
large stocks that drop 2%+ do not beat other stocks bought the same morning
over 1-5 days, at any drop size tested. Any value must come from the AI's
news research. To measure it, log each night's composite scores and compare
next-day returns of high vs low scores against same-morning stocks.

In the sample batch (2026-10-29), DELL, PANW, FN and CIEN all fell further the
next session (-10.8%, -3.9%, -6.1%, -8.2%; verified from Yahoo prices).
