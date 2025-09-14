import time
from app.services.coinbase_service import fetch_coinbase_prices

ASSETS = ["BTC", "ETH"]

def generate_signals(prices, history):
    signals = []
    for asset, price in prices.items():
        hist = history.get(asset, [])
        hist.append(price)
        history[asset] = hist[-20:]  # Keep last 20 prices
        if len(hist) >= 10:
            sma_short = sum(hist[-5:]) / 5
            sma_long = sum(hist[-10:]) / 10
            if sma_short > sma_long:
                signals.append({
                    "asset": asset,
                    "entry_price": price,
                    "signal": "buy",
                    "confidence": 0.8
                })
    return signals, history

def simulate_trade(signal, prices):
    asset = signal["asset"]
    entry = signal["entry_price"]
    time.sleep(1)  # For demo, use 1 second instead of 1 minute
    new_prices = fetch_coinbase_prices([asset])
    exit_price = new_prices.get(asset, entry)
    success = exit_price > entry
    return {
        "asset": asset,
        "entry_price": entry,
        "exit_price": exit_price,
        "success": success
    }

def evaluate_performance(trades):
    total_trades = len(trades)
    wins = sum(1 for t in trades if t["success"])
    losses = total_trades - wins
    win_rate = wins / total_trades if total_trades > 0 else 0
    return {
        "total_trades": total_trades,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate
    }

def run_ai_trading_simulation():
    history = {}
    trades = []
    for _ in range(2):  # Demo: run 2 trades
        prices = fetch_coinbase_prices(ASSETS)
        signals, history = generate_signals(prices, history)
        for s in signals:
            trade = simulate_trade(s, prices)
            trades.append(trade)
    performance = evaluate_performance(trades)
    return {
        "trades": trades,
        "performance": performance
    }
# app/services/ai_trading_service.py
# Live demo paper trading using Coinbase prices and simple signals
