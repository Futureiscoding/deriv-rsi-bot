import asyncio
import websockets
import json
from datetime import datetime

API_TOKEN = "dUhkgBjlZnDjDZb"
SYMBOL = "frxEURUSD"
TRADE_AMOUNT = 20
BUY_THRESHOLD = 30
SELL_THRESHOLD = 70
MAX_TRADES_PER_DAY = 4

price_history = []
trade_count = 0
today = datetime.utcnow().date()

def compute_rsi(prices, period=14):
    if len(prices) < period + 1:
        return None

    gains, losses = [], []
    for i in range(1, period + 1):
        delta = prices[-i] - prices[-i - 1]
        if delta >= 0:
            gains.append(delta)
        else:
            losses.append(-delta)

    avg_gain = sum(gains) / period if gains else 0
    avg_loss = sum(losses) / period if losses else 0.0001  # prevent division by zero

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

async def main():
    global trade_count, today

    uri = "wss://ws.deriv.com/websockets/v3?app_id=1089"
    async with websockets.connect(uri) as ws:
        # Authorize
        await ws.send(json.dumps({"authorize": API_TOKEN}))
        print("✅ Authorized")

        # Subscribe to ticks
        await ws.send(json.dumps({"ticks": SYMBOL, "subscribe": 1}))

        while True:
            msg = await ws.recv()
            data = json.loads(msg)

            if "tick" in data:
                price = float(data["tick"]["quote"])
                print(f"Tick: {price}")
                price_history.append(price)

                if len(price_history) > 100:
                    price_history.pop(0)

                rsi = compute_rsi(price_history)
                if rsi:
                    print(f"RSI: {rsi:.2f}")

                    now = datetime.utcnow().date()
                    if now != today:
                        trade_count = 0
                        today = now

                    if trade_count < MAX_TRADES_PER_DAY:
                        if rsi < BUY_THRESHOLD:
                            print("💹 BUY Signal")
                            await place_trade(ws, "CALL")
                            trade_count += 1
                        elif rsi > SELL_THRESHOLD:
                            print("🔻 SELL Signal")
                            await place_trade(ws, "PUT")
                            trade_count += 1
                    else:
                        print("🚫 Max trades reached for today")

async def place_trade(ws, contract_type):
    proposal = {
        "proposal": 1,
        "amount": TRADE_AMOUNT,
        "basis": "stake",
        "contract_type": contract_type,
        "currency": "USD",
        "duration": 5,
        "duration_unit": "t",
        "symbol": SYMBOL
    }
    await ws.send(json.dumps(proposal))

    while True:
        msg = await ws.recv()
        response = json.loads(msg)
        if "proposal" in response:
            buy_request = {
                "buy": response["proposal"]["id"],
                "price": TRADE_AMOUNT
            }
            await ws.send(json.dumps(buy_request))
            print(f"✅ Trade placed: {contract_type}")
            break

asyncio.run(main())




