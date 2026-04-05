import pandas as pd
import numpy as np
import yfinance as yf
import requests
import time
import os

# -----------------------------
# TELEGRAM SETTINGS
# -----------------------------
BOT_TOKEN = os.getenv("8716087264:AAGUQoucfM4V5S8S_ZrwWtXU6oEXrN0A7Fw")
CHAT_ID = os.getenv("946243778")

# -----------------------------
# STRATEGY SETTINGS
# -----------------------------
RR = 3
SLIPPAGE = 0.0005
MAX_ENTRY_BARS = 3

# -----------------------------
# TELEGRAM FUNCTION
# -----------------------------
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    requests.post(url, data=data)

# -----------------------------
# GLOBAL STATE
# -----------------------------
last_signal_time = None
active_setup = None  # store setup

# -----------------------------
# SAFE VALUE
# -----------------------------
def get_val(x):
    if isinstance(x, pd.Series):
        return float(x.iloc[0])
    return float(x)

# -----------------------------
# MAIN LOGIC
# -----------------------------
def check_signal():
    global last_signal_time, active_setup

    data = yf.download("GC=F", interval="1h", period="5d")

    if data.empty or len(data) < 60:
        return

    data.reset_index(inplace=True)

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    time_col = "Datetime" if "Datetime" in data.columns else data.columns[0]

    data["EMA50"] = data["Close"].ewm(span=50).mean()

    i = len(data) - 1

    mother = data.iloc[i-2]
    baby = data.iloc[i-1]

    mother_open = get_val(mother["Open"])
    mother_close = get_val(mother["Close"])
    mother_high = get_val(mother["High"])
    mother_low = get_val(mother["Low"])

    baby_open = get_val(baby["Open"])
    baby_close = get_val(baby["Close"])
    baby_high = get_val(baby["High"])
    baby_low = get_val(baby["Low"])

    ema_val = get_val(data["EMA50"].iloc[i-1])

    current_time = str(baby[time_col])

    # =========================
    # 1️⃣ CHECK NEW SETUP
    # =========================
    inside = (baby_high < mother_high) and (baby_low > mother_low)

    if inside and (mother_close < mother_open) and (baby_close > baby_open) and (baby_close > ema_val):

        if last_signal_time != current_time:

            entry = baby_high * (1 + SLIPPAGE)
            sl = mother_low
            risk = entry - sl
            tp = entry + RR * risk

            active_setup = {
                "entry": entry,
                "sl": sl,
                "tp": tp,
                "bars_left": MAX_ENTRY_BARS,
                "time": current_time
            }

            msg = f"""
📊 GOLD SETUP DETECTED

Entry: {round(entry,2)}
Stop Loss: {round(sl,2)}
Target: {round(tp,2)}

Waiting for breakout...
Valid for next 3 candles
"""
            send_telegram(msg)

            last_signal_time = current_time

    # =========================
    # 2️⃣ CHECK ENTRY TRIGGER
    # =========================
    if active_setup is not None:

        entry = active_setup["entry"]

        latest_high = get_val(data.iloc[i]["High"])

        # ENTRY TRIGGERED
        if latest_high >= entry:

            msg = f"""
🚀 GOLD ENTRY TRIGGERED

Entry: {round(entry,2)}
Stop Loss: {round(active_setup['sl'],2)}
Target: {round(active_setup['tp'],2)}

Trade is LIVE
"""
            send_telegram(msg)

            active_setup = None

        else:
            # reduce validity window
            active_setup["bars_left"] -= 1

            if active_setup["bars_left"] <= 0:
                active_setup = None

# -----------------------------
# MAIN LOOP
# -----------------------------
print("🚀 Bot started...")

send_telegram("✅ BOT UPDATED: ENTRY ALERT ACTIVE 🚀")

while True:
    try:
        check_signal()
        time.sleep(3600)
    except Exception as e:
        print("Error:", e)
        time.sleep(60)
