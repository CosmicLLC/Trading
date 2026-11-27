"""
Synthetic data generator for testing the Phase 1 pipeline without QC/EDGAR access.

Produces a CSV in the same schema as quantconnect_phase1_data_pull.py's output
(low_float_gap_candidates.csv), optionally with catalyst columns already joined
(as sec_edgar_catalyst_flag.py would add), and with a KNOWN, PLANTED relationship
between predictors and the fade outcome. Running phase1_analysis.py on this
lets you check that it (a) recovers an effect that is really there and
(b) does not invent one when there is none (--null).

THIS IS FAKE DATA. Nothing produced here says anything about real markets.

Usage:
    python synthetic_data.py out.csv [--n 1500] [--seed 0] [--null] [--no-catalyst]
"""

import argparse

import numpy as np
import pandas as pd

# Planted log-odds model for P(fade). Chosen so the gap and catalyst effects are
# clearly detectable at n~1000 and RVOL has no effect (a built-in negative control).
TRUE_COEFS = {
    "intercept": -0.5,
    "gap_pct": 0.02,        # bigger gaps fade more
    "catalyst_flag": -1.0,  # catalyst-backed gaps fade less
    "rvol": 0.0,            # no effect -- should NOT come out significant
}


def generate(n=1500, seed=0, null=False, with_catalyst=True):
    rng = np.random.default_rng(seed)

    dates = pd.bdate_range("2023-01-02", "2024-12-31")
    date = np.sort(rng.choice(dates, size=n))
    symbol = [f"SYN{i:03d}" for i in rng.integers(0, 300, size=n)]

    prior_close = np.round(rng.uniform(1, 20, size=n), 2)
    gap_pct = rng.lognormal(mean=np.log(25), sigma=0.7, size=n)  # mostly 5%-150%
    premarket_high = prior_close * (1 + gap_pct / 100)
    # pre-market low sits somewhere between prior close and the high
    premarket_low = prior_close + (premarket_high - prior_close) * rng.uniform(0.1, 0.7, size=n)
    premarket_volume = rng.lognormal(mean=12, sigma=1, size=n).round()
    rvol = rng.lognormal(mean=np.log(4), sigma=0.8, size=n)
    atr_pct = rng.uniform(4, 15, size=n)
    atr_normalized_gap = gap_pct / atr_pct

    catalyst_flag = rng.binomial(1, 0.35, size=n)
    # days_since_catalyst consistent with the flag (0/1 if flagged, 2..6 otherwise)
    days_since = np.where(
        catalyst_flag == 1, rng.integers(0, 2, size=n), rng.integers(2, 7, size=n)
    )

    if null:
        p_fade = np.full(n, 0.45)
    else:
        logit = (
            TRUE_COEFS["intercept"]
            + TRUE_COEFS["gap_pct"] * gap_pct
            + TRUE_COEFS["catalyst_flag"] * catalyst_flag
            + TRUE_COEFS["rvol"] * rvol
        )
        p_fade = 1 / (1 + np.exp(-logit))
    faded = rng.binomial(1, p_fade)

    # Translate the latent outcome into a price so the pipeline derives the label
    # itself: faded -> price ends below the pre-market low, else above the high.
    below = premarket_low * rng.uniform(0.85, 0.99, size=n)
    above = premarket_high * rng.uniform(1.01, 1.2, size=n)
    price_after_lookahead = np.where(faded == 1, below, above)

    # A few rows with a missing lookahead price (halts / no bars), as the real pull can produce.
    missing = rng.random(n) < 0.02
    price_after_lookahead = np.where(missing, np.nan, price_after_lookahead)

    df = pd.DataFrame({
        "symbol": symbol,
        "date": pd.to_datetime(date).date,
        "prior_close": prior_close,
        "premarket_high": premarket_high.round(4),
        "premarket_low": premarket_low.round(4),
        "gap_pct": gap_pct.round(4),
        "premarket_volume": premarket_volume,
        "rvol": rvol.round(4),
        "atr_normalized_gap": atr_normalized_gap.round(4),
        "price_after_lookahead": price_after_lookahead.round(4),
    })
    if with_catalyst:
        df["catalyst_flag"] = catalyst_flag
        df["days_since_catalyst"] = days_since
    return df


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--n", type=int, default=1500)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--null", action="store_true", help="no planted effect")
    ap.add_argument("--no-catalyst", action="store_true", help="omit catalyst columns (raw QC schema)")
    a = ap.parse_args()
    generate(a.n, a.seed, a.null, not a.no_catalyst).to_csv(a.out, index=False)
    print(f"Wrote {a.out}")
