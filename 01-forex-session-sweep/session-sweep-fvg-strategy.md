# Session Liquidity Sweep + FVG Reversal — Complete Trading Playbook

## The Core Thesis

Retail stop-losses and breakout orders cluster right above/below obvious session highs and lows. Institutional order flow needs liquidity to fill large positions, so price is statistically drawn to those pools before reversing in the intended direction. Your strategy is built to catch that reversal, not the breakout.

The sequence: **liquidity is engineered (swept) → displacement occurs → an imbalance (FVG) is left behind → price returns to that imbalance → you enter in the direction of the new move → you ride it to the next pool of liquidity.**

---

## 1. Core Concepts, Defined Precisely

**Session ranges**
- **Asia session:** ~7:00 PM–4:00 AM EST (Tokyo/Sydney overlap drives it)
- **London session:** ~2:00/3:00 AM–11:00/12:00 PM EST
- **New York session:** ~7:00/8:00 AM–4:00/5:00 PM EST
- Adjust ±1 hour around US/UK daylight saving transitions (they don't shift on the same dates).

**ICT Killzones (highest-probability windows within sessions)**
- London Open Killzone: 2:00–5:00 AM EST
- NY AM Killzone: 7:00–10:00 AM EST (overlaps London close — highest volume window of the day)
- NY PM Killzone: 1:30–4:00 PM EST
- Asian Killzone: 8:00 PM–12:00 AM EST

**Liquidity sweep (a.k.a. "raid" or "stop hunt")**
Price trades beyond a marked high or low — ideally with a quick wick/rejection rather than a slow grind — then snaps back inside the range. A sweep that doesn't snap back and instead keeps running is *not* a sweep; it's a breakout, and taking a reversal entry against it is how this strategy loses money (see Failure Modes below).

**Fair Value Gap (FVG)**
A 3-candle imbalance: candle 1's high doesn't overlap candle 3's low (bullish FVG) or candle 1's low doesn't overlap candle 3's high (bearish FVG). It represents a gap in two-sided trading — price moved so fast one side didn't get to trade there, and it's a magnet for a retrace.

**Market Structure Shift (MSS) / Change in State of Delivery (CISD)**
After the sweep, price must break a recent minor swing point in the *new* intended direction. This is your confirmation that order flow has actually shifted — without it, you're just guessing that the sweep will reverse.

**Draws on liquidity (DOL)**
The next magnet price is likely headed toward. In priority order, typically:
1. Nearest untested FVG / order block in the direction of your trade
2. Equal highs or equal lows (double top/bottom liquidity)
3. The opposing session's high/low (if London swept the low, Asia's high is a draw)
4. Previous day's high/low
5. Weekly open, or previous week's high/low
6. Daily/weekly bias target if you're using higher-timeframe context (e.g., a much larger imbalance days back)

---

## 2. Step-by-Step Execution

1. **Mark Asia high/low and London high/low** on your chart the moment each session closes (or update live as each session develops).
2. **Wait for a sweep** of one of those levels — by London or NY session price action taking out Asia's high/low, or NY taking out London's.
3. **Drop to the 1-minute chart** the instant the sweep happens.
4. **Look for displacement** — a sharp, strong-bodied move away from the sweep level. This is what leaves the FVG behind.
5. **Identify the FVG** created by that displacement leg.
6. **Wait for price to return into the FVG** — either to the near edge, to the 50% level (called "consequent encroachment," the more common conservative entry), or full fill.
7. **Confirm MSS/CISD** — a break of the most recent minor 1-min swing point in your trade direction. Ideally this happens *before or during* the FVG retrace, not after — you want structure confirming the reversal, not just hoping the FVG holds.
8. **Enter** on the FVG retrace once structure is confirmed.
9. **Stop loss** goes just beyond the sweep wick (the actual high/low that got raided) — that's your invalidation point. If price takes that out again, your read was wrong.
10. **Target the nearest draw on liquidity**, not a fixed RR. Scale or trail toward the next pool if there's a case for continuation (e.g., HTF bias agrees).

---

## 3. Entry Checklist (use this literally, every trade)

- [ ] Asia and London highs/lows marked
- [ ] A session high or low has been swept with a clear wick/rejection, not a slow grind
- [ ] Displacement candle(s) followed the sweep
- [ ] A clean FVG exists on the 1-min from that displacement
- [ ] Price has returned to the FVG (edge, CE, or full fill — pick one and be consistent)
- [ ] A market structure shift/CISD confirms direction, ideally before entry
- [ ] There is an identifiable draw on liquidity within reasonable distance — if there's nothing to draw toward, skip the trade regardless of how clean the FVG looks
- [ ] No major red-folder news (CPI, NFP, FOMC, etc.) due in the next 30 minutes

---

## 4. Risk Management

- **Stop placement:** beyond the sweep wick, not beyond the FVG. Using the wick keeps your invalidation tight and specific to the thesis being wrong (liquidity didn't actually reverse there).
- **Position size:** risk a fixed % of account per trade (0.5–1% is standard for a strategy with this many discretionary judgment calls — MSS confirmation and DOL selection are both subjective, so don't size like it's mechanical).
- **Expectancy math matters more than any single RR.** Since you're now targeting variable draws on liquidity instead of fixed 1:2, your average win size will vary trade to trade. Track actual R multiples achieved, not planned, and compute your real expectancy: (win% × avg win R) − (loss% × avg loss R). This strategy typically has win rates in the 40–55% range with average wins well above 1.5R when target selection is done well — the edge comes from win *size*, not win frequency.
- **Daily loss limit:** because 1-min entries invite overtrading (every session produces a sweep of *something*), set a hard stop on trades-per-day or losses-per-day before you start.

---

## 5. Why Your Adjustment (Draws on Liquidity vs. Fixed RR) Is Correct

Fixed 1:2 RR caps winners at a number that has nothing to do with market structure — you'll get stopped out of trades that were right, just early, and you'll cut trades short that had a much larger DOL available (e.g., an FVG entry off the London low sweep that had the entire Asian high, a previous day high, *and* a weekly open all stacked as draws above it). Targeting the actual next liquidity pool means your reward is dictated by where price is actually likely to go, not an arbitrary multiple. The tradeoff: it's more subjective, so you need a consistent rule for *which* DOL you target (nearest one? or hold for the furthest one with HTF support?) — decide this before you're in a live trade, not while you're in one.

---

## 6. Failure Modes — What Actually Breaks This Strategy

1. **Trading every sweep, not just clean ones.** Not every level that gets tapped is a real liquidity raid. Slow grinds through a level with no wick, no rejection, and no displacement afterward are usually genuine directional moves, not sweeps — reversal entries here are how the strategy bleeds.
2. **No higher-timeframe bias filter.** Taking every 1-min sweep+FVG setup regardless of the daily/4H trend is the single biggest reason win rate collapses. Use a higher-timeframe directional bias (previous day's close vs. open, 4H structure, weekly profile) to only take reversals that align with — or are due for — the bigger picture. Counter-trend sweep reversals in strong trending conditions fail far more often.
3. **FVG without displacement.** A gap that forms from a weak, small-bodied candle isn't the same signal as one from a genuine displacement move. Weight the quality of the move that created the FVG, not just the gap's existence.
4. **No MSS confirmation, or MSS after the fact.** Entering purely because "price is in the FVG" without a structural break confirming the shift is trading hope, not the setup.
5. **News-driven sweeps.** A sweep 10 minutes before CPI or NFP isn't liquidity engineering — it's positioning ahead of a scheduled catalyst, and the "reversal" logic doesn't apply the same way. Filter news windows out entirely.
6. **1-minute noise and overtrading.** The lower the timeframe, the more setups *look* valid and the more you'll take that shouldn't be taken. Backtest with a hard cap on trades per session before going live.
7. **Ambiguous DOL selection creating hindsight bias in backtesting.** It's easy to look back and say "the target was obviously the previous day high" after the fact. Write down your target *before* the trade plays out during backtesting, or your win-rate numbers will be inflated garbage.

---

## 7. Backtesting & Journaling Framework

Track, per trade:
- Session and which level swept (Asia high, London low, etc.)
- Time of day (killzone or outside one)
- HTF bias at the time (aligned or counter-trend)
- FVG entry method used (edge / CE / full fill)
- Planned DOL target (written down before trade closes)
- Actual R achieved
- Whether MSS occurred before or after entry

Run this for a minimum of 50–100 trades in sim/backtest before sizing up. You're specifically trying to answer: does aligning with HTF bias meaningfully change your win rate and average R? Most traders running this style find the answer is yes, and it's the single highest-leverage filter available.

---

## 8. Tools

- **TradingView**: manual session marking, or free/paid indicators for auto-plotting session high/low boxes and FVGs (search "ICT killzones," "FVG indicator," "liquidity sweep indicator" in the public library).
- **Replay mode** (TradingView Premium or similar) for backtesting without emotional/hindsight contamination — it forces you to make decisions candle-by-candle instead of looking at the completed chart.

---

## Bottom Line

The strategy is theoretically sound — it's grounded in how order flow and liquidity actually function around obvious levels. Your edge won't come from finding "the" perfect FVG entry; it'll come from (1) filtering out sweeps that aren't real engineered liquidity, (2) requiring genuine structural confirmation before entry, and (3) disciplined, pre-committed target selection using the DOL hierarchy above rather than picking whichever level looks convenient after the trade's already won.

*Not financial advice — this is a breakdown of a discretionary technical trading methodology, not a recommendation to trade any specific instrument or size. Backtest thoroughly before risking real capital.*
