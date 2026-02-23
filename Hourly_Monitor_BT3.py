import pandas as pd
from kiteconnect import KiteConnect
import datetime as dt
import os
import logging

# LOGGING
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename="logs/intraday_monitor.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# KITE CONNECT
kite = KiteConnect(api_key="")
kite.set_access_token("")

# PATHS
INPUT_FILE = "output/Daily_Screener_BT3.xlsx"
OUTPUT_FILE = "output/Hourly_Monitor_BT3.xlsx"

# LOAD DAILY SCREENER
watchlist = pd.read_excel(INPUT_FILE)

if watchlist.empty:
    print("Daily Screener is empty. Nothing to monitor.")
    exit()

symbols = watchlist["SYMBOL"].unique().tolist()
logging.info(f"Monitoring {len(symbols)} stocks")

# HELPER FUNCTION
def fetch_last_60min_candle(symbol):
    try:
        token = kite.ltp(f"NSE:{symbol}")[f"NSE:{symbol}"]["instrument_token"]
        to_date = dt.datetime.now()
        from_date = to_date - dt.timedelta(days=5)

        data = kite.historical_data(
            instrument_token=token,
            from_date=from_date,
            to_date=to_date,
            interval="60minute"
        )

        df = pd.DataFrame(data)
        if len(df) < 2:
            return None

        df = df.sort_values("date")
        return df.iloc[-1]  # latest closed candle
    except Exception as e:
        logging.error(f"{symbol} 60min fetch error: {e}")
        return None

# MONITOR LOGIC
results = []

for _, row in watchlist.iterrows():
    symbol = row["SYMBOL"]
    entry_level = row["ENTRY_LEVEL"]

    candle = fetch_last_60min_candle(symbol)
    if candle is None:
        continue

    close_price = candle["close"]

    if close_price > entry_level:
        signal = "BUY"
        comment = "60-min breakout confirmed"
    else:
        signal = "WAIT"
        comment = "No breakout yet"

    results.append({
        "SYMBOL": symbol,
        "ENTRY_LEVEL": entry_level,
        "LAST_60MIN_CLOSE": round(close_price, 2),
        "SIGNAL": signal,
        "TARGET": row["TARGET"],
        "STOP": row["STOP"],
        "COMMENT": comment
    })

# OUTPUT
output_df = pd.DataFrame(results)

os.makedirs("output", exist_ok=True)
output_df.sort_values(["SIGNAL", "SYMBOL"], ascending=[False, True]).to_excel(
    OUTPUT_FILE, index=False
)

logging.info("Hourly monitor updated")

print("Hourly Monitor BT3 completed.")
