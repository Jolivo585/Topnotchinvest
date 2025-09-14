import os
import httpx
import requests

API_URL = os.getenv("COINBASE_API_URL", "https://api.commerce.coinbase.com")
API_KEY = os.getenv("COINBASE_API_KEY", "")

HEADERS = {
    "X-CC-Api-Key": API_KEY,
    "X-CC-Version": "2018-03-22",
    "Content-Type": "application/json"
}

def fetch_coinbase_prices(assets):
    prices = {}
    for asset in assets:
        symbol = asset + "-USD"
        url = f"https://api.coinbase.com/v2/prices/{symbol}/spot"
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        prices[asset] = float(data["data"]["amount"])
    return prices

async def create_charge(name: str, description: str, amount: float, currency: str = "USD"):
    payload = {
        "name": name,
        "description": description,
        "local_price": {"amount": f"{amount:.2f}", "currency": currency},
        "pricing_type": "fixed_price"
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f"{API_URL}/charges", json=payload, headers=HEADERS)
        resp.raise_for_status()
        return resp.json()

async def get_charge(charge_id: str):
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{API_URL}/charges/{charge_id}", headers=HEADERS)
        resp.raise_for_status()
        return resp.json()

async def list_charges():
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{API_URL}/charges", headers=HEADERS)
        resp.raise_for_status()
        return resp.json()