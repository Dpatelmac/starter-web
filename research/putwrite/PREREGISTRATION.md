# Pre-registered test 4: cash-secured put-write layer on idle cash

Written and committed **before** any returns of the put-write index were
computed or looked at (2026-11-01). Only data availability was checked:
CBOE S&P 500 PutWrite index (^PUT) daily from 1996-08-02, VIX from 1990,
13-week T-bill yield (^IRX), SPY with dividends from 1993.

## Portfolio and market context

- Paper portfolio (IBKR via SIGNUM): NAV $23,941; **64% cash**; stock sleeve
  63% chips/tech, beta 2.15. Unchanged since 2026-10-14.
- Fed held at 3.75-4.00% on 2026-10-28 (two dissents for a hike); futures
  price ~83% odds of a hike on 2026-12-09. T-bills 3.97%; VIX 19.4; S&P 500
  forward P/E ~18.7 (below 5- and 10-year averages). Nasdaq -5% in October on
  AI-spending worries. This week: midterms (Tue), Apple/AMD/Qualcomm earnings,
  jobs report (Fri).

## Proposal

| | Rule |
|---|---|
| Universe | S&P 500 options (SPY, or XSP/SPX for Section 1256 tax treatment) |
| Horizon | Ongoing; monthly cycle; judged over years |
| Entry | Each month on the standard expiry (third Friday), sell 1-month at-the-money puts, fully cash-secured: notional = collateral, collateral held in T-bills (CBOE PutWrite methodology) |
| Exit | Puts expire or settle at expiry; roll to the next month. No early buyback |
| Sizing | Layer = 50% of NAV (about $12,000 of today's $15,282 cash); remaining cash stays in T-bills as a buffer. Never leveraged: notional never exceeds collateral |
| Max exposure | Equity delta of the layer starts near 0.5 x 50% = ~25% of NAV, rising toward 50% of NAV in a selloff |
| Max acceptable drawdown | If the layer falls 25% below its peak, stop writing new puts and review |

## Thesis

Index option prices usually exceed the moves that follow (the variance risk
premium): buyers pay for crash insurance, sellers are paid to bear it. A
put-writer earns that premium plus T-bill interest on the collateral.

## What would invalidate it

- The premium shrinking from crowding (option-income ETFs, 0DTE selling since
  about 2020): check 2020-2026 separately.
- Crash losses: short puts lose almost like stock in sharp falls, with
  limited upside. Check 2008, 2020, 2022.
- Implied volatility no longer exceeding realized volatility on average.

## Test

- Data: ^PUT daily (verified index data, total return including T-bill
  interest; excludes trading costs and taxes).
- **Out-of-sample split:** 1996-08 to 2007-06 (before the index was launched
  and before most of the literature) vs 2007-07 to 2026-10 (after).
- Layer scaled to 50% of NAV with the rest in T-bills is the portfolio-level
  view; the pass test is on the layer itself vs benchmarks below.

### Assumptions (labelled, not data)

- Trading cost: 0.5% a year drag (base), 1.0% (stress). SPY at-the-money
  monthly puts typically trade a few cents wide on a ~$15 premium; the base
  case is deliberately conservative.
- Taxes (US taxable account): Section 1256 index options taxed 60% long-term
  (15%) / 40% short-term (32%) = 21.8% on option profits each year, with
  losses carried forward; T-bill interest 32%. SPY dividends 15% each year;
  SPY gains 15% when sold at the end. Shown both before and after tax.

### Benchmarks

SPY buy and hold; T-bills (what the idle cash earns today); a 50/50
SPY/T-bill mix rebalanced monthly (similar average equity exposure, so it
tests whether the layer is more than just lower beta).

### Pass criteria (base costs, after tax, in BOTH periods)

1. Sharpe ratio (excess over T-bills) higher than SPY's.
2. Sharpe ratio higher than the 50/50 SPY/T-bill mix's.
3. Maximum drawdown smaller than SPY's.
4. After-tax annual return above after-tax T-bills.

Reported for context, not used to decide: the same with a 200-day SPY filter
(skip writing when SPY is below its 200-day average at the roll), 2020-2026
alone, the VIX-vs-realized-volatility gap since 1990, and stress costs.

## Decision rule

Pass: present the layer for paper trading (manual in IBKR; SIGNUM bots can't
trade options), for review only. Fail: recommend keeping the cash in T-bills.
