"""
Backtest starter: Asia session liquidity sweep + FVG reversal
Data: OANDA v20 API (free practice account)
Engine: backtesting.py

pip install backtesting requests pandas --break-system-packages

THIS IS A SKELETON, NOT A VALIDATED SYSTEM. It only implements the
bullish Asia-low-sweep case, with no MSS confirmation and a crude
session window. Read the "What's missing" section at the bottom
before drawing any conclusions from its output.
"""

import requests
import pandas as pd
from backtesting import Backtest, Strategy

OANDA_URL = "https://api-fxpractice.oanda.com/v3"
API_TOKEN = "YOUR_TOKEN_HERE"
HEADERS = {"Authorization": f"Bearer {API_TOKEN}"}


def fetch_candles(instrument="EUR_USD", granularity="M1", start=None, end=None):
    """Pull historical M1 candles from OANDA, paginated (max 5000/request)."""
    all_candles = []
    params = {"granularity": granularity, "price": "M", "count": 5000}
    if start:
        params["from"] = start
    while True:
        r = requests.get(
            f"{OANDA_URL}/instruments/{instrument}/candles",
            headers=HEADERS, params=params
        )
        r.raise_for_status()
        data = r.json()["candles"]
        if not data:
            break
        all_candles.extend(data)
        last_time = data[-1]["time"]
        if end and last_time >= end:
            break
        params["from"] = last_time
        if len(data) < 5000:
            break
    return all_candles


def to_dataframe(candles):
    rows = []
    for c in candles:
        if not c["complete"]:
            continue
        rows.append({
            "Time": pd.to_datetime(c["time"]),
            "Open": float(c["mid"]["o"]),
            "High": float(c["mid"]["h"]),
            "Low": float(c["mid"]["l"]),
            "Close": float(c["mid"]["c"]),
            "Volume": c["volume"],
        })
    return pd.DataFrame(rows).set_index("Time")


class SessionSweepFVG(Strategy):
    spread_pips = 0.8      # realistic EUR/USD retail spread — DO NOT set to 0
    slippage_pips = 0.3    # extra slippage on market fills
    risk_pct = 0.01
    asia_start_hour = 0    # UTC — adjust to match your data feed's timezone
    asia_end_hour = 8

    def init(self):
        self.asia_high = None
        self.asia_low = None

    def next(self):
        t = self.data.index[-1]
        hour = t.hour

        # mark Asia session range
        if self.asia_start_hour <= hour < self.asia_end_hour:
            h, l = self.data.High[-1], self.data.Low[-1]
            self.asia_high = h if self.asia_high is None else max(self.asia_high, h)
            self.asia_low = l if self.asia_low is None else min(self.asia_low, l)
            return  # don't trade during session formation

        if self.asia_high is None or self.asia_low is None:
            return

        price = self.data.Close[-1]
        low = self.data.Low[-1]

        swept_low = low < self.asia_low and price > self.asia_low
        if swept_low and len(self.data.Close) > 3 and not self.position:
            c1_high = self.data.High[-3]
            c3_low = self.data.Low[-1]
            fvg_bullish = c1_high < c3_low

            if fvg_bullish:
                pip = 0.0001
                entry = price + (self.spread_pips + self.slippage_pips) * pip
                stop = low - 2 * pip
                target = self.asia_high
                risk_per_unit = entry - stop
                if risk_per_unit > 0 and target > entry:
                    size = max(1, int((self.equity * self.risk_pct) / risk_per_unit))
                    self.buy(size=size, sl=stop, tp=target)


if __name__ == "__main__":
    candles = fetch_candles(start="2023-01-01T00:00:00Z", end="2024-01-01T00:00:00Z")
    df = to_dataframe(candles)
    print(f"Loaded {len(df)} candles")

    bt = Backtest(df, SessionSweepFVG, cash=10_000, commission=0.0, exclusive_orders=True)
    stats = bt.run()
    print(stats)
    bt.plot()

"""
WHAT'S MISSING (fix these before trusting any result):
1. Bearish case (London-high sweep -> bearish FVG) isn't implemented — only
   tests half the strategy.
2. No market structure shift confirmation — this is the piece the research
   flagged as doing the real discretionary work. Without it you're testing
   a weaker, more mechanical version of the strategy than you'd actually trade.
3. Session windows are crude UTC hour ranges — verify against your data feed's
   actual timestamp timezone before trusting the Asia/London boundaries.
4. Target uses only the opposing session level as the draw on liquidity —
   real trading would also consider equal highs/lows, prior-day levels, etc.
5. No walk-forward split. Once this runs cleanly:
   - Split your data 70/30 by time (not randomly)
   - Tune nothing on the 70%, just run it as-is
   - Check whether performance holds on the unseen 30%
   - Then check year-by-year P&L, not just the aggregate — one good year
     hiding two bad ones is the single most common false positive
6. No significance test. Compute a t-stat on the trade returns
   (scipy.stats.ttest_1samp against zero) — the research bar to take this
   seriously is t >= 2 across 100+ trades spanning multiple years.
"""
