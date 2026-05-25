import requests
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator, MACD
from ta.volatility import BollingerBands
import time
import threading

BALANCE = 1000
RISK_PER_TRADE = 0.05
MIN_SCORE = 75
CHECK_EVERY_SECONDS = 20
TRADE_DURATION_SECONDS = 300  # 5 minutes

bot_running = False
trades = []
balance = BALANCE


def get_btc_data():
    url = "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1m&limit=120"
    data = requests.get(url, timeout=10).json()

    rows = []
    for candle in data:
        rows.append({
            "open": float(candle[1]),
            "high": float(candle[2]),
            "low": float(candle[3]),
            "close": float(candle[4]),
            "volume": float(candle[5])
        })

    return pd.DataFrame(rows)


def analyze_market():
    df = get_btc_data()

    df["rsi"] = RSIIndicator(df["close"], window=14).rsi()
    df["ema20"] = EMAIndicator(df["close"], window=20).ema_indicator()
    df["ema50"] = EMAIndicator(df["close"], window=50).ema_indicator()

    macd = MACD(df["close"])
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()

    bb = BollingerBands(df["close"])
    df["bb_high"] = bb.bollinger_hband()
    df["bb_low"] = bb.bollinger_lband()

    last = df.iloc[-1]
    prev = df.iloc[-2]

    score = 50
    direction = "WAIT"

    if last["ema20"] > last["ema50"]:
        score += 20
        direction = "UP"
    else:
        score -= 20
        direction = "DOWN"

    if 40 <= last["rsi"] <= 60:
        score += 10

    if last["macd"] > last["macd_signal"]:
        score += 15
    else:
        score -= 15

    if last["close"] > prev["close"]:
        score += 5
    else:
        score -= 5

    volume_avg = df["volume"].tail(20).mean()
    if last["volume"] > volume_avg:
        score += 10

    if last["close"] > last["bb_high"] or last["close"] < last["bb_low"]:
        score -= 15

    score = max(0, min(100, score))

    return {
        "price": last["close"],
        "score": score,
        "direction": direction,
        "rsi": last["rsi"]
    }


def run_paper_trade(signal):
    global balance

    entry_price = signal["price"]
    direction = signal["direction"]
    trade_amount = balance * RISK_PER_TRADE

    print("\nTRADE OPENED ✅")
    print("Direction:", direction)
    print("Entry Price:", entry_price)
    print("Confidence Score:", str(signal["score"]) + "%")
    print("Paper Amount:", round(trade_amount, 2))
    print("Waiting 5 minutes...")

    time.sleep(TRADE_DURATION_SECONDS)

    exit_data = get_btc_data()
    exit_price = exit_data.iloc[-1]["close"]

    if direction == "UP":
        win = exit_price > entry_price
    else:
        win = exit_price < entry_price

    profit = trade_amount * 0.80 if win else -trade_amount
    balance += profit

    trade = {
        "direction": direction,
        "entry": entry_price,
        "exit": exit_price,
        "win": win,
        "profit": profit
    }

    trades.append(trade)

    print("\nTRADE CLOSED")
    print("Exit Price:", exit_price)
    print("Result:", "WIN ✅" if win else "LOSS ❌")
    print("Profit/Loss:", round(profit, 2))
    print("Current Paper Balance:", round(balance, 2))


def bot_loop():
    global bot_running

    print("\nBot started.")
    print("The bot is scanning for trades...")

    while bot_running:
        try:
            signal = analyze_market()

            print("\nScanning...")
            print("BTC Price:", signal["price"])
            print("RSI:", round(signal["rsi"], 2))
            print("Direction:", signal["direction"])
            print("Confidence Score:", str(signal["score"]) + "%")

            if signal["score"] >= MIN_SCORE and signal["direction"] != "WAIT":
                run_paper_trade(signal)
            else:
                print("No trade found.")

            time.sleep(CHECK_EVERY_SECONDS)

        except Exception as e:
            print("Error:", e)
            time.sleep(10)

    print("\nBot stopped.")


def show_summary():
    total = len(trades)
    wins = sum(1 for t in trades if t["win"])
    losses = total - wins
    total_profit = balance - BALANCE
    win_rate = (wins / total * 100) if total > 0 else 0

    print("\n========== BOT SUMMARY ==========")
    print("Total Trades:", total)
    print("Wins:", wins)
    print("Losses:", losses)
    print("Win Rate:", round(win_rate, 2), "%")
    print("Starting Balance:", BALANCE)
    print("Current Balance:", round(balance, 2))
    print("Total Profit/Loss:", round(total_profit, 2))
    print("=================================")


print("Manual BTC Paper Trading Bot")
print("Type start to run the bot.")
print("Type exit to stop the bot and show results.")

while True:
    command = input("\nCommand: ").lower()

    if command == "start":
        if not bot_running:
            bot_running = True
            thread = threading.Thread(target=bot_loop)
            thread.start()
        else:
            print("Bot is already running.")

    elif command == "exit":
        bot_running = False
        time.sleep(1)
        show_summary()
        break

    else:
        print("Unknown command. Type start or exit.")