"""
Quick connectivity test — confirms your OANDA token works and you can
pull data, before running the full year-long backtest.

pip install requests python-dotenv --break-system-packages
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()  # reads the .env file in the same folder

TOKEN = os.environ.get("OANDA_TOKEN")

if not TOKEN:
    print("ERROR: OANDA_TOKEN not found. Check your .env file exists and has")
    print("the line: OANDA_TOKEN=your_token_here (no quotes, no spaces around =)")
    exit(1)

OANDA_URL = "https://api-fxpractice.oanda.com/v3"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

print("Testing connection to OANDA...")

r = requests.get(
    f"{OANDA_URL}/instruments/EUR_USD/candles",
    headers=HEADERS,
    params={"granularity": "M1", "count": 5, "price": "M"}
)

if r.status_code == 200:
    candles = r.json()["candles"]
    print(f"SUCCESS. Pulled {len(candles)} candles.\n")
    for c in candles:
        print(f"{c['time']}  O:{c['mid']['o']}  H:{c['mid']['h']}  "
              f"L:{c['mid']['l']}  C:{c['mid']['c']}")
else:
    print(f"FAILED. Status code: {r.status_code}")
    print(r.text)
    print("\nCommon fixes:")
    print("- Token wrong or expired: regenerate it in your OANDA account settings")
    print("- Using a live-account token against the practice URL (or vice versa)")
    print("- Missing 'Bearer ' prefix — should be handled automatically above")
