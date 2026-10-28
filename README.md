# SPY Pine Script Strategy Library

TradingView strategies for **SPY**, written in Pine Script v6. Each file is self-contained: paste it into TradingView and backtest it on TradingView's own data.

| # | Strategy | Style | Timeframe | Direction |
|---|---|---|---|---|
| 01 | [Golden Cross (50/200 SMA)](strategies/01-golden-cross.pine) | Trend | 1D | Long |
| 02 | [RSI(2) Mean Reversion](strategies/02-rsi2-mean-reversion.pine) | Mean reversion | 1D | Long |
| 03 | [Bollinger Band Reversion](strategies/03-bollinger-reversion.pine) | Mean reversion | 1D, 4H | Long |
| 04 | [Donchian Breakout](strategies/04-donchian-breakout.pine) | Breakout | 1D, 4H, 1H | Long (short optional) |
| 05 | [MACD + 200 EMA Trend](strategies/05-macd-trend.pine) | Trend | 1D, 4H | Long |
| 06 | [Supertrend](strategies/06-supertrend.pine) | Trend | 1H, 4H, 1D | Long (short optional) |
| 07 | [Opening Range Breakout](strategies/07-opening-range-breakout.pine) | Intraday breakout | 5m (1m–30m) | Long + short |

## Rules at a glance

- **01 Golden Cross**: buy when the 50 SMA crosses above the 200 SMA, sell when it crosses back below.
- **02 RSI(2)**: buy when RSI(2) < 10 and price is above the 200 SMA. Sell when the close is above the 5 SMA, or after 10 bars.
- **03 Bollinger**: buy a close below the lower band (20, 2σ) while above the 200 SMA. Sell at the middle band. Optional % stop.
- **04 Donchian**: buy a close above the prior 20-bar high, sell on a close below the prior 10-bar low.
- **05 MACD**: buy when MACD crosses above its signal line while above the 200 EMA. Sell on the opposite cross or a close below the EMA.
- **06 Supertrend**: buy when Supertrend (10, 3) flips up, exit (or reverse) when it flips down.
- **07 ORB**: the 9:30–10:00 NY range sets the levels. Take the first close outside the range, stop at the other side, target 2R, flat by 15:50. One trade per day.

## How to use

1. Open a **SPY** chart in TradingView and set the timeframe listed above.
2. Open **Pine Editor** at the bottom of the screen, delete the default code, and paste in a strategy file.
3. Click **Save**, then **Add to chart**.
4. Open the **Strategy Tester** tab to see net profit, win rate, max drawdown, the trade list, and the equity curve.
5. Change settings with the ⚙️ icon on the strategy's name on the chart.

## Default backtest settings

All strategies share the same defaults so results can be compared:

- Initial capital: $10,000
- Position size: 100% of equity
- Commission: 0 (most US brokers charge none for ETFs)
- Slippage: 1 tick ($0.01)
- Orders fill at the **next bar's open**. ORB fills at the bar's close so it can exit before the session ends.

## Adding a strategy

Copy [`templates/strategy-template.pine`](templates/strategy-template.pine) to `strategies/NN-name.pine`, keep the same `strategy()` defaults, and add a row to the table above.

## Notes

- Compare each result against **buy-and-hold SPY** over the same dates. Many strategies lose to it.
- Intraday history on TradingView depends on your plan. Daily history goes back to 1993.
- Beware of overfitting: settings tuned to the past rarely work as well in the future.
- For research and education only. This is not financial advice. Paper trade before risking money.
