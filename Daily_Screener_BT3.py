import pandas as pd
import numpy as np
from kiteconnect import KiteConnect
import datetime as dt
import os
import logging

# LOGGING
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename="logs/daily_screener.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# KITE CONNECT
kite = KiteConnect(api_key="")
kite.set_access_token("")
# PATHS
SYMBOL_FILE = "data/symbols.xlsx"
OUTPUT_FILE = "output/Daily_Screener_BT3.xlsx"

# LOAD SYMBOLS
symbols_df = pd.read_excel(SYMBOL_FILE, sheet_name="Sheet1")
symbols = symbols_df["SYMBOL"].str.upper().unique().tolist()

logging.info(f"Loaded {len(symbols)} symbols")
# HELPER FUNCTIONS
def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    rs = gain.rolling(period).mean() / loss.rolling(period).mean()
    return 100 - (100 / (1 + rs))


def fetch_daily_data(symbol, days=120):
    try:
        token = kite.ltp(f"NSE:{symbol}")[f"NSE:{symbol}"]["instrument_token"]
        to_date = dt.date.today()
        from_date = to_date - dt.timedelta(days=days)
        data = kite.historical_data(
            instrument_token=token,
            from_date=from_date,
            to_date=to_date,
            interval="day"
        )
        return pd.DataFrame(data)
    except Exception as e:
        logging.error(f"{symbol} data fetch failed: {e}")
        return None
    
    # SCREENER LOGIC
results = []

for symbol in symbols:
    df = fetch_daily_data(symbol)
    if df is None or len(df) < 50:
        continue

    df = df.sort_values("date").reset_index(drop=True)

    # Indicators
    df["rsi"] = rsi(df["close"])
    df["rsi_change_3d"] = df["rsi"].diff(3)
    df["vol_20_avg"] = df["volume"].rolling(20).mean()

    # Box (15-day)
    df["box_high"] = df["high"].rolling(15).max().shift(1)
    df["box_low"] = df["low"].rolling(15).min().shift(1)
    df["box_range_pct"] = (df["box_high"] - df["box_low"]) / df["box_low"]

    range_5 = df["high"].rolling(5).max() - df["low"].rolling(5).min()
    range_10 = df["high"].rolling(10).max() - df["low"].rolling(10).min()

    latest = df.iloc[-1]

    # Filters
    box_tight = (
        latest["box_range_pct"] <= 0.12 and
        range_5.iloc[-1] < range_10.iloc[-1]
    )

    volume_surge = latest["volume"] > 1.3 * latest["vol_20_avg"]

    rsi_ready = (
        latest["rsi"] >= 50 and
        latest["rsi_change_3d"] >= 3
    )

    breakout_ready = latest["close"] <= latest["box_high"]

    if box_tight and volume_surge and rsi_ready:
        results.append({
            "SYMBOL": symbol,
            "CMP": round(latest["close"], 2),
            "ENTRY_LEVEL": round(latest["box_high"], 2),
            "TARGET": round(latest["box_high"] * 1.10, 2),
            "STOP": round(latest["box_high"] * 0.97, 2),
            "BOX_TIGHT": "✅",
            "VOLUME_SURGE": "✅",
            "RSI_READY": "✅",
            "STATUS": "WATCH",
            "COMMENT": "BT3 setup ready – wait for 60m breakout"
        })

# OUTPUT
output_df = pd.DataFrame(results)

if not output_df.empty:
    os.makedirs("output", exist_ok=True)
    output_df.sort_values("SYMBOL").to_excel(OUTPUT_FILE, index=False)
    logging.info(f"Screener generated with {len(output_df)} stocks")
else:
    logging.info("No stocks qualified today")

print("Daily Screener BT3 completed.")

print(f"Stocks shortlisted: {len(output_df)}")
