# Flowchart (text version of `flowchart.jpg`)

1. **FLAT, no LITE shares.** This is the start, and where it returns after every sale.
2. **Track the highest price.** The high resets at the start and after every sale.
3. **Is price ≤ High − $60?** (dip found) If no, keep tracking the high.
4. **Track the lowest price** after the drop.
5. **Is price ≥ Low + 0.5%?** (rebound) If no, keep tracking the low.
6. **BUY floor(cap ÷ price) shares.** Limit order (DAY), cancelled if unfilled in about 60 s.
7. **Place a $95 trailing SELL stop** at Schwab, GTC (lives overnight and over weekends).
8. **Monitor BOTH conditions:**
   - **$95 trail triggered?** (Schwab sells) → **SOLD, stop loss** (loss ≈ $35–$95 per share)
   - **Price ≥ Buy + $60?** (profit target) → **Cancel the $95 stop** (wait for Schwab to confirm) →
     **Place a $10 trailing SELL stop** (GTC) → the trail rises with price → **price drops $10 from its high?**
     → **SOLD, profit** (profit ≈ $50+ per share)
9. **Back to FLAT.** The high resets and pending edits apply, then repeat.

## How it maps to the Pine strategy

- Dip and target checks use the bar's low and high (an intrabar touch counts). The rebound check uses the
  bar's close, so not every daily bar counts as a rebound.
- The day limit order cancelled after about 60 s can't be reproduced on bars; it becomes a market entry at the next open.
- The trailing stops ratchet once per bar (at the close), not tick by tick as at the broker, so there is no lookahead.
- Only one stop is ever active: the $95 stop is replaced by the $10 stop when the target is hit.
