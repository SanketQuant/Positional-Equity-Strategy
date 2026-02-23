# Positional Stock Strategy (Python)

End-to-end intraday trading system:
- Backtesting
- Every Morning stock selection
- Hourly trade confirmation
- Live position monitoring

## Files

- `src/backtest_strategy.py`: Backtests the strategy on historical data.
- `src/morning_stock_filter.py`: Runs daily to find which stocks to trade.
- `src/hourly_trade_confirmation.py`: Checks intraday conditions for entry.
- `src/position_monitor.py`: Decides whether to hold, exit, or adjust positions.

## How to Run

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
