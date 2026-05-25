from flask import Flask, render_template_string, redirect
import threading
import time
import requests

app = Flask(__name__)

# RESET EVERYTHING
bot_running = False

START_BALANCE = 1000
balance = 1000

TRADE_PERCENT = 0.15

ROUND_SECONDS = 300
ENTRY_SECONDS_LEFT = 90

MIN_AI_PROBABILITY = 0.75
MIN_MARKET_PRICE = 0.75
MAX_MARKET_PRICE = 0.85

# RESET TRADE HISTORY
trades = []

candles = []

def get_btc_candles():

    url = "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1m&limit=30"

    data = requests.get(url, timeout=10).json()

    result = []

    for c in data:

        result.append({
            "x": int(c[0]),
            "o": float(c[1]),
            "h": float(c[2]),
            "l": float(c[3]),
            "c": float(c[4])
        })

    return result

def get_seconds_left():

    return ROUND_SECONDS - (int(time.time()) % ROUND_SECONDS)

def analyze_market(candles):

    last = candles[-1]["c"]
    old = candles[-6]["c"]

    direction = "UP" if last > old else "DOWN"

    move = abs(last - old)

    volatility = max(
        c["h"] - c["l"] for c in candles[-5:]
    )

    ai_probability = 0.50

    if move > 10:
        ai_probability += 0.10

    if move > 25:
        ai_probability += 0.10

    if volatility < 80:
        ai_probability += 0.10

    if volatility < 50:
        ai_probability += 0.05

    ai_probability = min(ai_probability, 0.90)

    return direction, ai_probability, volatility

def fake_polymarket_price(ai_probability):

    return round(
        max(0.75, min(0.85, ai_probability + 0.05)),
        2
    )

def should_enter_trade(ai_probability, market_price, seconds_left):

    if seconds_left > ENTRY_SECONDS_LEFT:
        return False, "Waiting until last 1:30"

    if ai_probability < MIN_AI_PROBABILITY:
        return False, "AI probability too low"

    if market_price < MIN_MARKET_PRICE:
        return False, "Market price too low"

    if market_price > MAX_MARKET_PRICE:
        return False, "Market price too expensive"

    return True, "GOOD TRADE FOUND"

def bot_loop():

    global bot_running
    global balance
    global candles

    while bot_running:

        try:

            candles = get_btc_candles()

            current_price = candles[-1]["c"]

            seconds_left = get_seconds_left()

            direction, ai_probability, volatility = analyze_market(candles)

            market_price = fake_polymarket_price(ai_probability)

            enter, reason = should_enter_trade(
                ai_probability,
                market_price,
                seconds_left
            )

            if enter:

                price_to_beat = current_price

                trade_amount = balance * TRADE_PERCENT

                print("TRADE OPENED")

                print("Direction:", direction)

                print("Price To Beat:", price_to_beat)

                print("Waiting until round ends...")

                time.sleep(seconds_left)

                candles = get_btc_candles()

                final_price = candles[-1]["c"]

                if direction == "UP":
                    win = final_price > price_to_beat
                else:
                    win = final_price < price_to_beat

                if win:

                    payout = trade_amount / market_price

                    profit = payout - trade_amount

                else:

                    profit = -trade_amount

                balance += profit

                trades.append({

                    "direction": direction,

                    "trade_amount": round(trade_amount, 2),

                    "price_to_beat": round(price_to_beat, 2),

                    "final_price": round(final_price, 2),

                    "result": "WIN ✅" if win else "LOSS ❌",

                    "profit": round(profit, 2),

                    "score": round(ai_probability * 100, 2),

                    "market_price": market_price
                })

            time.sleep(5)

        except Exception as e:

            print("ERROR:", e)

            time.sleep(5)

@app.route("/")
def home():

    global candles

    if not candles:

        try:
            candles = get_btc_candles()
        except:
            candles = []

    status = "RUNNING ✅" if bot_running else "STOPPED ⛔"

    seconds_left = get_seconds_left()

    if candles:

        current_price = candles[-1]["c"]

        direction, ai_probability, volatility = analyze_market(candles)

        market_price = fake_polymarket_price(ai_probability)

        enter, reason = should_enter_trade(
            ai_probability,
            market_price,
            seconds_left
        )

    else:

        current_price = "Loading..."

        direction = "Loading..."

        ai_probability = 0

        market_price = 0

        reason = "Loading..."

    total = len(trades)

    wins = len([
        t for t in trades
        if "WIN" in t["result"]
    ])

    losses = total - wins

    total_profit = balance - START_BALANCE

    candle_data = str(candles)

    rows = ""

    for t in trades[-10:][::-1]:

        rows += f"""
        <tr>
            <td>{t['direction']}</td>
            <td>${t['trade_amount']}</td>
            <td>{t['price_to_beat']}</td>
            <td>{t['final_price']}</td>
            <td>{t['result']}</td>
            <td>{t['score']}%</td>
            <td>{t['market_price']}</td>
            <td>${t['profit']}</td>
        </tr>
        """

    html = f"""

<html>

<head>

<meta name="viewport" content="width=device-width, initial-scale=1">

<meta http-equiv="refresh" content="5">

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<script src="https://cdn.jsdelivr.net/npm/luxon"></script>

<script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-luxon"></script>

<script src="https://cdn.jsdelivr.net/npm/chartjs-chart-financial"></script>

<style>

body {{
    font-family: Arial;
    background: #111;
    color: white;
    padding: 20px;
}}

.card {{
    background: #1e1e1e;
    padding: 15px;
    border-radius: 15px;
    margin-bottom: 15px;
}}

button {{
    padding: 15px;
    font-size: 18px;
    border-radius: 12px;
    border: none;
    margin: 5px;
}}

.start-btn {{
    background: #00c853;
    color: white;
}}

.stop-btn {{
    background: #d50000;
    color: white;
}}

table {{
    width: 100%;
    color: white;
    font-size: 13px;
}}

td, th {{
    padding: 6px;
    text-align: center;
}}

</style>

</head>

<body>

<h1>BTC Polymarket Bot 🚀</h1>

<div class="card">

<h2>Status: {status}</h2>

<h2>BTC Current Price: {current_price}</h2>

<h3>Time Left: {seconds_left}s</h3>

<h3>Direction Prediction: {direction}</h3>

<h3>AI Probability: {round(ai_probability * 100, 2)}%</h3>

<h3>Demo Polymarket Price: {market_price}</h3>

<h3>Reason: {reason}</h3>

<h3>Balance: ${round(balance, 2)}</h3>

<h3>Total Profit/Loss: ${round(total_profit, 2)}</h3>

</div>

<a href="/start">
<button class="start-btn">
START BOT
</button>
</a>

<a href="/stop">
<button class="stop-btn">
STOP BOT
</button>
</a>

<div class="card">

<h3>Total Trades: {total}</h3>

<h3>Wins: {wins}</h3>

<h3>Losses: {losses}</h3>

</div>

<div class="card">

<canvas id="btcChart"></canvas>

</div>

<div class="card">

<h3>Last Trades</h3>

<table>

<tr>
<th>Side</th>
<th>Trade $</th>
<th>Price To Beat</th>
<th>Final Price</th>
<th>Result</th>
<th>AI</th>
<th>Price</th>
<th>P/L</th>
</tr>

{rows}

</table>

</div>

<script>

const candleData = {candle_data};

new Chart(document.getElementById('btcChart'), {{

    type: 'candlestick',

    data: {{

        datasets: [{{
            label: 'BTC Candles',
            data: candleData
        }}]

    }},

    options: {{

        responsive: true,

        scales: {{
            x: {{
                type: 'time'
            }}
        }}

    }}

}});

</script>

</body>

</html>

"""

    return render_template_string(html)

@app.route("/start")
def start():

    global bot_running

    if not bot_running:

        bot_running = True

        threading.Thread(target=bot_loop).start()

    return redirect("/")

@app.route("/stop")
def stop():

    global bot_running

    bot_running = False

    return redirect("/")

if __name__ == "__main__":

    app.run(host="0.0.0.0", port=5000)