import pandas as pd
from datetime import datetime
from kiteconnect import KiteConnect
import os

# KITE CONNECT SETUP
kite = KiteConnect(api_key="")
kite.set_access_token("")

# PATHS
BASE_DIR = os.getcwd()
INPUT_FILE = os.path.join(BASE_DIR, "Manual_Positions_file.xlsx")
OUTPUT_FILE = os.path.join(BASE_DIR, "output", "Position_Manager_Output_BT3.xlsx")

# LOAD POSITIONS
positions = pd.read_excel(INPUT_FILE)

positions.columns = positions.columns.str.upper()

# Only OPEN positions
open_positions = positions[positions["POSITION_STATUS"] == "OPEN"].copy()

if open_positions.empty:
    print("No open positions to evaluate.")
    exit()

# FETCH LIVE PRICES FROM KITE
symbols = open_positions["SYMBOL"].unique().tolist()
kite_symbols = [f"NSE:{sym}" for sym in symbols]

ltp_data = kite.ltp(kite_symbols)

price_map = {
    sym.replace("NSE:", ""): ltp_data[sym]["last_price"]
    for sym in ltp_data
}

open_positions["CMP"] = open_positions["SYMBOL"].map(price_map)

# CALCULATIONS
open_positions["ENTRY_DATE"] = pd.to_datetime(open_positions["ENTRY_DATE"])
open_positions["HOLDING_DAYS"] = (datetime.now() - open_positions["ENTRY_DATE"]).dt.days

open_positions["TARGET_PRICE"] = open_positions["ENTRY_PRICE"] * 1.10
open_positions["STOP_PRICE"] = open_positions["ENTRY_PRICE"] * 0.97

open_positions["PNL_%"] = (
    (open_positions["CMP"] - open_positions["ENTRY_PRICE"])
    / open_positions["ENTRY_PRICE"]
) * 100

open_positions["MTM_PNL"] = (
    open_positions["CMP"] - open_positions["ENTRY_PRICE"]
) * open_positions["QTY"]

# DECISION ENGINE (BT3)
def decision(row):
    if row["CMP"] >= row["TARGET_PRICE"]:
        return "EXIT", "TARGET", "Target hit (+10%)"
    elif row["CMP"] <= row["STOP_PRICE"]:
        return "EXIT", "STOP", "Stop-loss hit (-3%)"
    elif row["PNL_%"] >= 7:
        return "ATTENTION", "NEAR_TARGET", "Near target – watch closely"
    elif row["PNL_%"] <= -2:
        return "ATTENTION", "NEAR_STOP", "Near stop – watch risk"
    else:
        return "HOLD", "NONE", "Structure intact"

results = open_positions.apply(
    lambda row: pd.Series(decision(row), index=["STATUS", "EXIT_TYPE", "REASON"]),
    axis=1
)

open_positions = pd.concat([open_positions, results], axis=1)

# FINAL OUTPUT
output_cols = [
    "SYMBOL",
    "ENTRY_DATE",
    "ENTRY_PRICE",
    "CMP",
    "QTY",
    "PNL_%",
    "MTM_PNL",
    "HOLDING_DAYS",
    "TARGET_PRICE",
    "STOP_PRICE",
    "STATUS",
    "EXIT_TYPE",
    "REASON",
    "NOTES",
]

open_positions[output_cols].to_excel(OUTPUT_FILE, index=False)

print("Position Manager updated successfully.")

print(f"Output saved to: {OUTPUT_FILE}")
