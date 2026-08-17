# Automating the Session Sweep + FVG Strategy

## Path 1 (fastest, do this first): TradingView Pine Script → Webhook → n8n

You don't need to build a data pipeline at all for this. TradingView already computes session boxes, FVGs, and sweeps via free community indicators, and its alert system can fire a webhook to any URL — including an n8n webhook trigger — the moment a condition is met.

**Setup:**
1. Add a free ICT/SMC indicator from the public library — search "Fair Value Gap," "Session Highs Lows," "Liquidity Sweep," or "ICT Concepts" on TradingView. LuxAlgo, ChartPrime, and several independent authors publish free versions that plot exactly what you need.
2. Set alerts on the indicator's built-in conditions (sweep detected, FVG formed, structure shift). Most of these indicators expose `alertcondition()` calls you can trigger directly.
3. In the alert dialog, choose "Webhook URL" and point it at an n8n Webhook node. Message body — use a JSON template so n8n can parse it cleanly:

```json
{
  "symbol": "{{ticker}}",
  "event": "fvg_reversal_bullish",
  "session_swept": "asia_low",
  "price": {{close}},
  "time": "{{time}}"
}
```

4. **n8n workflow:**
   - Webhook trigger (receives the alert)
   - Filter node: check current time against your killzone windows, and against a news-blackout window (see Low-Hanging Fruit #1 below) — drop the alert if either fails
   - Airtable/Google Sheets node: log the alert as a row (this becomes your auto-journal — see #2)
   - Telegram or Discord node: push a formatted message to your phone

This gets you real-time alerts with zero custom data infrastructure, using tools you already run.

**Limitation:** TradingView alerts fire on indicator logic you didn't write, so you're trusting someone else's FVG/sweep definitions. Fine for alerting; not rigorous enough to trust for backtesting stats.

---

## Path 2: Your own loop (for backtesting and eventual auto-execution)

If you want full control over the exact detection logic (matching your rules precisely) and a path toward backtesting or auto-execution, pull the data yourself.

**Data source — use OANDA's v20 API, not a generic market data API.** Reasoning: it's free with a live or demo account, gives you 1-minute historical granularity going back years, streams live prices, *and* the same API places trades — one integration instead of three. (Alternatives if you don't want an OANDA account: Twelve Data — 800 free requests/day, or Tiingo — 1,000 free requests/day, forex-specific and clean data. Both are pull-only, no execution.)

**Loop architecture (Python, runs on a cron or always-on VM):**

```python
import requests, pandas as pd
from datetime import datetime, timedelta

OANDA_URL = "https://api-fxpractice.oanda.com/v3"  # practice; swap to live URL when ready
HEADERS = {"Authorization": "Bearer YOUR_API_TOKEN"}

def get_candles(instrument, granularity="M1", count=200):
    r = requests.get(
        f"{OANDA_URL}/instruments/{instrument}/candles",
        headers=HEADERS,
        params={"granularity": granularity, "count": count, "price": "M"}
    )
    return r.json()["candles"]

def mark_session_range(candles, start_hour, end_hour):
    # filter candles within session window, return (high, low)
    session = [c for c in candles if start_hour <= parse_hour(c["time"]) < end_hour]
    highs = [float(c["mid"]["h"]) for c in session]
    lows = [float(c["mid"]["l"]) for c in session]
    return max(highs), min(lows)

def detect_sweep(candles, level, direction):
    # direction: "high" or "low" — did price wick beyond level and close back inside?
    last = candles[-1]
    high, low, close = float(last["mid"]["h"]), float(last["mid"]["l"]), float(last["mid"]["c"])
    if direction == "high":
        return high > level and close < level
    else:
        return low < level and close > level

def detect_fvg(c1, c2, c3):
    # bullish FVG: c1 high < c3 low ; bearish FVG: c1 low > c3 high
    c1h, c1l = float(c1["mid"]["h"]), float(c1["mid"]["l"])
    c3h, c3l = float(c3["mid"]["h"]), float(c3["mid"]["l"])
    if c1h < c3l:
        return {"type": "bullish", "top": c3l, "bottom": c1h}
    if c1l > c3h:
        return {"type": "bearish", "top": c1l, "bottom": c3h}
    return None

def detect_mss(candles, swing_point, direction):
    # did the most recent close break the prior swing high/low in trade direction?
    last_close = float(candles[-1]["mid"]["c"])
    if direction == "bullish":
        return last_close > swing_point
    else:
        return last_close < swing_point

# Main loop — run every 60s during killzones only
def run():
    candles = get_candles("EUR_USD")
    asia_high, asia_low = mark_session_range(candles, start_hour=19, end_hour=4)
    # ... sweep -> fvg -> mss check chain here, fire webhook/alert/order on full confirmation
```

This is a skeleton, not a finished bot — the swing-point tracking and killzone windowing need real state management across candles, not a single snapshot. But it's the right shape: pull candles, mark sessions, check sweep → FVG → MSS in sequence, and only act when all three align.

**Auto-execution:** OANDA's `/v3/accounts/{id}/orders` endpoint takes a market or limit order with a stop-loss attached in the same request. Technically trivial to wire up once detection is solid. **Don't wire it up until you've backtested extensively** — see the caution below.

---

## Other Low-Hanging Fruit

**1. Economic calendar blackout filter.** ForexFactory publishes a free calendar feed. Pull it once a day, store the high-impact event times, and have your n8n filter (or Python loop) suppress any alert within 15–30 minutes of a red-folder event. This single filter probably improves your win rate more than any tweak to the FVG logic itself.

**2. Auto-journaling.** Every alert that fires gets logged as a row in Airtable/Google Sheets automatically — session, level swept, FVG zone, planned DOL target, timestamp. This is exactly the backtesting framework from the strategy playbook, except it fills itself in instead of you typing it after the fact. Add a column you update manually with the actual outcome (R achieved), and you've got a self-building dataset.

**3. Position size calculator.** A simple n8n workflow or Google Sheets formula: input entry price, stop price (the sweep wick), and your fixed risk % → output lot size. Removes math errors under time pressure on the 1-min chart.

**4. Backtesting harness.** Pull 6–12 months of OANDA M1 history and run your exact detection logic (Path 2 code, extended) across it programmatically instead of eyeballing charts. This is the highest-value automation on this whole list — it tells you your actual win rate and expectancy before you risk anything, which right now is still an assumption.

**5. Telegram/Discord bot.** Since you're mobile-first, route every confirmed setup to a Telegram bot instead of Discord — lower latency, better mobile notification handling for time-sensitive alerts.

**6. MetaTrader Expert Advisor (MQL4/5), if your broker supports it.** If you already trade through a broker with MT4/5, you can code this entire strategy natively as an EA — detection and execution in one place, no external API or webhook chain needed. This is the standard retail-forex path and may be less infrastructure than the n8n/OANDA route if MT4/5 is already your platform.

---

## The One Caution

MSS confirmation and draw-on-liquidity target selection are the two most subjective parts of this strategy — exactly the parts hardest to codify correctly and easiest to get subtly wrong in code. Automate detection and alerting first, keep entry/target decisions manual for a while, and only move toward auto-execution once your logged, backtested stats say the codified version matches your discretionary judgment. Skipping straight to full auto-execution on unvalidated logic is the fastest way to lose money faster than you would by hand.

## Suggested Build Order
1. TradingView indicator + webhook → n8n → Telegram alert (this week, low effort)
2. Add Airtable auto-journaling to that same n8n flow
3. Add the news-calendar blackout filter
4. Build the Python backtest harness against OANDA historical data to get real win-rate/expectancy numbers
5. Only after step 4 validates the edge: consider semi-automated or full execution via OANDA API or an MT4/5 EA
