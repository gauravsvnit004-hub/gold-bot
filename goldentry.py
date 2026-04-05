import pandas as pd
import numpy as np
import yfinance as yf
import requests
import time

# -----------------------------
# TELEGRAM SETTINGS
# -----------------------------
BOT_TOKEN = "8716087264:AAGUQoucfM4V5S8S_ZrwWtXU6oEXrN0A7Fw"
CHAT_ID = "946243778"

# -----------------------------
# STRATEGY SETTINGS
# -----------------------------
RR = 3
SLIPPAGE = 0.0005

# -----------------------------
# TELEGRAM FUNCTION
# -----------------------------
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    requests.post(url, data=data)

# -----------------------------
# GLOBAL (avoid duplicates)
# -----------------------------
last_signal_time = None

# -----------------------------
# SAFE VALUE EXTRACTOR
# -----------------------------
def get_val(x):
    if isinstance(x, pd.Series):
        return float(x.iloc[0])
    return float(x)

# -----------------------------
# MAIN STRATEGY FUNCTION
# -----------------------------
def check_signal():
    global last_signal_time

    try:
        data = yf.download("GC=F", interval="1h", period="5d")

        if data.empty or len(data) < 3:
            return

        data.reset_index(inplace=True)

        # Fix multi-index issue
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        # Detect time column
        if "Datetime" in data.columns:
            time_col = "Datetime"
        else:
            time_col = data.columns[0]

        # EMA
        data["EMA50"] = data["Close"].ewm(span=50).mean()

        i = len(data) - 1

        mother = data.iloc[i-2]
        baby = data.iloc[i-1]

        # Extract scalar values safely
        mother_open = get_val(mother["Open"])
        mother_close = get_val(mother["Close"])
        mother_high = get_val(mother["High"])
        mother_low = get_val(mother["Low"])

        baby_open = get_val(baby["Open"])
        baby_close = get_val(baby["Close"])
        baby_high = get_val(baby["High"])
        baby_low = get_val(baby["Low"])

        ema_val = get_val(data["EMA50"].iloc[i-1])

        # Avoid duplicate signals
        current_time = str(baby[time_col])
        if last_signal_time == current_time:
            return

        # -----------------------------
        # STRATEGY CONDITIONS
        # -----------------------------
        inside = (baby_high < mother_high) and (baby_low > mother_low)

        if not inside:
            return

        if not (mother_close < mother_open):
            return

        if not (baby_close > baby_open):
            return

        if not (baby_close > ema_val):
            return

        # -----------------------------
        # ENTRY / SL / TP
        # -----------------------------
        entry = baby_high * (1 + SLIPPAGE)
        sl = mother_low
        risk = entry - sl

        if risk <= 0:
            return

        tp = entry + RR * risk

        # -----------------------------
        # SEND TELEGRAM ALERT
        # -----------------------------
        msg = f"""
🚀 GOLD LONG SETUP

Entry: {round(entry,2)}
Stop Loss: {round(sl,2)}
Target (3R): {round(tp,2)}

Pattern: Inside Candle Breakout
Trend: Above EMA50

Valid for next 3 candles
"""

        send_telegram(msg)
        print("✅ Signal sent!")

        last_signal_time = current_time

    except Exception as e:
        print("❌ Error:", e)

# -----------------------------
# MAIN LOOP
# -----------------------------
print("🚀 Bot started...")
send_telegram("✅ BOT IS LIVE AND WORKING 🚀")

while True:
    check_signal()
    time.sleep(3600)  # runs every 1 hour
