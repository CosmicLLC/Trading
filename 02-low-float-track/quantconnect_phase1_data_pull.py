# Low-Float Gap Sweep — Phase 1 Data Pull
# Run this inside QuantConnect's Research.ipynb (cloud, free tier, no credit card
# required for up to ~1 year of history). Paste each "# --- CELL ---" section into
# its own notebook cell.
#
# STATUS: field names below are now sourced from QuantConnect's published docs
# (see comments), but this still has not been executed against a live QC account
# from this environment (QC's domain isn't reachable here). Confirm both API calls
# work on the first real run before trusting anything downstream -- QC has shifted
# between PascalCase (qb.AddEquity) and snake_case (qb.add_equity) across API
# versions; try snake_case first (current v2 API), fall back to PascalCase if you
# hit an AttributeError.

# --- CELL 1: Setup ---
qb = QuantBook()

import pandas as pd
import numpy as np

# --- CELL 2: Build a point-in-time low-float candidate universe ---
# QuantConnect's Fundamental data (Morningstar-sourced) is point-in-time by design,
# which is exactly what avoids the look-ahead bias the project brief warns about.
#
# Shares-outstanding field (per QC docs, "Equity Fundamental Data"):
#   fundamental.CompanyProfile.SharesOutstanding
#   In DataFrame/history form this comes back as `companyprofile.share_class_level_shares_outstanding`.
# Confirm the field returns non-null values for a handful of known low-float names
# before trusting the screen below.

LOW_FLOAT_MAX_SHARES = 20_000_000  # parameter, not fixed truth -- adjust and re-run
LOW_FLOAT_MAX_PRICE = 20            # parameter

start_date = datetime(2023, 1, 1)
end_date = datetime(2024, 12, 31)

def is_low_float_candidate(fundamental):
    try:
        shares_out = fundamental.CompanyProfile.SharesOutstanding  # confirmed field name, verify non-null on first run
        price = fundamental.Price
        return shares_out is not None and shares_out < LOW_FLOAT_MAX_SHARES and price < LOW_FLOAT_MAX_PRICE
    except Exception:
        return False

# Pull a historical fundamental universe for a sample of dates (extend to full range once working).
# IMPORTANT FIX: qb.GetFundamental(d, "QC500") was a placeholder -- QC500 is a curated
# large-cap list and will exclude almost every genuine low-float microcap. Calling
# qb.GetFundamental(d) with NO universe/symbol argument returns Fundamental objects for
# every US equity in the Morningstar dataset that was trading on that date, including
# names that have since been delisted -- this is what gives us survivorship-bias-free,
# all-US-equities coverage. Verify this on the first real run: print len(fundamentals)
# and confirm it's in the thousands (QC's dataset covers ~8,000 US equities), not ~500.
sample_dates = pd.date_range(start_date, end_date, freq='W-MON')  # weekly snapshots to start
candidates_by_date = {}

for d in sample_dates:
    try:
        fundamentals = qb.GetFundamental(d)  # no universe arg = all US equities for that date
        low_float = [f for f in fundamentals if is_low_float_candidate(f)]
        candidates_by_date[d] = [f.Symbol for f in low_float]
    except Exception as e:
        print(f"Fundamental pull failed for {d}: {e}")

total_candidates = sum(len(v) for v in candidates_by_date.values())
print(f"Sampled {len(candidates_by_date)} dates, {total_candidates} low-float candidate rows total")
# Sanity check per the brief's task list: before scaling up, manually verify 5-10 of
# these candidate/date pairs against a known gap day (e.g. a finviz/chart screenshot)
# to confirm the float and price filters are behaving as expected.

# --- CELL 3: Pull minute bars with extended (pre-market) hours for each candidate ---
RVOL_LOOKBACK_DAYS = 20  # trailing average window, parameter

def get_gap_data(symbol, event_date):
    """
    Pulls minute bars including pre-market session for the event date and the
    prior RVOL_LOOKBACK_DAYS trading days, computes gap_pct, pre-market high/low,
    a same-time-of-day RVOL ratio, and a 14-day ATR-normalized gap.
    """
    qb.AddEquity(symbol, Resolution.Minute, extendedMarketHours=True)

    window_start = event_date - timedelta(days=RVOL_LOOKBACK_DAYS * 2)  # buffer for weekends/holidays
    window_end = event_date + timedelta(days=1)

    history = qb.History(symbol, window_start, window_end, Resolution.Minute)
    if history.empty:
        return None

    history = history.reset_index()
    history['date'] = history['time'].dt.date

    event_day = history[history['date'] == event_date.date()]
    prior_days = history[history['date'] < event_date.date()]

    if event_day.empty or prior_days.empty:
        return None

    prior_close = prior_days[prior_days['date'] == prior_days['date'].max()].iloc[-1]['close']

    premarket = event_day[event_day['time'].dt.hour < 9]  # before 9:30 ET regular open
    if premarket.empty:
        return None

    premarket_high = premarket['high'].max()
    premarket_low = premarket['low'].min()
    gap_pct = (premarket_high - prior_close) / prior_close * 100
    premarket_volume = premarket['volume'].sum()

    # RVOL: today's premarket volume vs trailing N-day average premarket volume,
    # same time-of-day window (pre-9:30), computed over the actual trading days
    # pulled above rather than a single prior day.
    prior_trading_days = sorted(prior_days['date'].unique())[-RVOL_LOOKBACK_DAYS:]
    prior_premarket_volumes = []
    for d in prior_trading_days:
        day_rows = prior_days[(prior_days['date'] == d) & (prior_days['time'].dt.hour < 9)]
        if not day_rows.empty:
            prior_premarket_volumes.append(day_rows['volume'].sum())
    avg_prior_premarket_volume = np.mean(prior_premarket_volumes) if prior_premarket_volumes else np.nan
    rvol = premarket_volume / avg_prior_premarket_volume if avg_prior_premarket_volume else np.nan

    # 14-day ATR (using daily high/low/close resampled from the pulled minute bars)
    daily = history.groupby('date').agg(high=('high', 'max'), low=('low', 'min'), close=('close', 'last'))
    daily = daily[daily.index < event_date.date()].tail(14)
    if len(daily) >= 2:
        prev_close = daily['close'].shift(1)
        tr = pd.concat([
            daily['high'] - daily['low'],
            (daily['high'] - prev_close).abs(),
            (daily['low'] - prev_close).abs(),
        ], axis=1).max(axis=1)
        atr_14 = tr.mean()
        atr_normalized_gap = gap_pct / (atr_14 / prior_close * 100) if atr_14 else np.nan
    else:
        atr_normalized_gap = np.nan

    return {
        'symbol': str(symbol),
        'date': event_date.date(),
        'prior_close': prior_close,
        'premarket_high': premarket_high,
        'premarket_low': premarket_low,
        'gap_pct': gap_pct,
        'premarket_volume': premarket_volume,
        'rvol': rvol,
        'atr_normalized_gap': atr_normalized_gap,
    }

# --- CELL 4: Assemble results ---
results = []
for d, symbols in candidates_by_date.items():
    for sym in symbols:
        row = get_gap_data(sym, d)
        if row is not None:
            results.append(row)

df = pd.DataFrame(results)
print(f"Collected {len(df)} candidate gap events")
df.head(20)

# --- CELL 5: Export for the statistical analysis phase ---
# This CSV is the handoff point to sec_edgar_catalyst_flag.py (adds catalyst_flag /
# days_since_catalyst) and then phase1_analysis.py (outcome_label, conditional
# probability tables, logistic regression).
df.to_csv('low_float_gap_candidates.csv', index=False)

# --- WHAT'S STILL MANUAL / UNVERIFIED, NEXT ---
# 1. Run this in an actual QC Research notebook and confirm CompanyProfile.SharesOutstanding
#    returns non-null values and qb.GetFundamental(d) (no args) returns thousands of
#    rows per date, not ~500 -- if either assumption is wrong, this whole pull is invalid.
# 2. Manually verify 5-10 of the resulting candidate/date rows against known gap days.
# 3. Check whether AlgoSeek's OTC exclusion is cutting the candidate list too thin
#    (target: 100+ qualifying events after the full pipeline runs) -- if too thin,
#    that's the trigger to evaluate FirstRate Data, per the project brief, not a
#    reason to loosen the float/gap thresholds.
# 4. Once this file's output looks sane, run sec_edgar_catalyst_flag.py against it,
#    then phase1_analysis.py for the outcome_label + statistical tests.
