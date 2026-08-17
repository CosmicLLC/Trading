"""
Low-Float Gap Sweep — Catalyst Flag (SEC EDGAR 8-K, self-sourced, free)

Joins a binary catalyst_flag and days_since_catalyst onto the candidate CSV
produced by quantconnect_phase1_data_pull.py, using SEC EDGAR's free full-text
search / submissions API. No sentiment analysis, no vendor -- presence/absence
of an 8-K filing only, per the project brief's exclusions.

SEC EDGAR requires a descriptive User-Agent identifying the requester (name +
contact email) on every request, or it will reject calls. Set EDGAR_USER_AGENT
below before running.

Run locally with: python sec_edgar_catalyst_flag.py low_float_gap_candidates.csv
"""

import sys
import time
import json
from datetime import datetime, timedelta

import pandas as pd
import requests

EDGAR_USER_AGENT = "REPLACE ME: Your Name your-email@example.com"  # required by SEC, fill this in
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
DAYS_SINCE_STALE_CAP = 5  # per brief: bucket anything beyond this as "stale"
CATALYST_WINDOW_HOURS = 16  # per brief: 8-K within prior 16 hours counts

_session = requests.Session()
_session.headers.update({"User-Agent": EDGAR_USER_AGENT})


def load_ticker_to_cik():
    resp = _session.get(TICKER_MAP_URL, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return {v["ticker"].upper(): v["cik_str"] for v in data.values()}


def get_8k_filing_dates(cik, ticker_to_cache):
    """Returns a sorted list of 8-K filing datetimes (filing date, no time-of-day
    granularity available from this endpoint -- see caveat below) for a given CIK."""
    if cik in ticker_to_cache:
        return ticker_to_cache[cik]
    url = SUBMISSIONS_URL.format(cik=cik)
    try:
        resp = _session.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"CIK {cik}: submissions fetch failed: {e}")
        ticker_to_cache[cik] = []
        return []

    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    eightk_dates = sorted(
        datetime.strptime(d, "%Y-%m-%d") for f, d in zip(forms, dates) if f == "8-K"
    )
    ticker_to_cache[cik] = eightk_dates
    return eightk_dates


def compute_catalyst_fields(event_date, eightk_dates):
    """
    CAVEAT (must be documented, per the brief's "no discretionary judgment" rule):
    EDGAR's submissions endpoint gives filing DATE only, not filing TIME. The
    project brief's catalyst_flag definition is "within the prior 16 hours,"
    which implies same-day-before-open or prior-evening precision that this
    endpoint cannot provide. As an explicit, documented proxy: treat any 8-K
    filed on the event date itself OR the prior calendar day as catalyst_flag=1
    (days_since_catalyst=0 or 1 respectively). This is a coarser proxy than the
    brief's ideal definition -- if EDGAR's full-text search API (which does
    expose more granular timestamps in some cases) turns out to be needed for
    precision, that's a follow-up, not a blocker for Phase 1's first pass.
    """
    event_date = pd.Timestamp(event_date).normalize()
    if not eightk_dates:
        return 0, DAYS_SINCE_STALE_CAP + 1

    days_since = min(
        (event_date - pd.Timestamp(d).normalize()).days
        for d in eightk_dates
        if pd.Timestamp(d).normalize() <= event_date
    ) if any(pd.Timestamp(d).normalize() <= event_date for d in eightk_dates) else None

    if days_since is None or days_since < 0:
        return 0, DAYS_SINCE_STALE_CAP + 1

    flag = 1 if days_since <= 1 else 0
    bucketed = days_since if days_since <= DAYS_SINCE_STALE_CAP else DAYS_SINCE_STALE_CAP + 1
    return flag, bucketed


def main(input_csv, output_csv="low_float_gap_with_catalyst.csv"):
    if "REPLACE ME" in EDGAR_USER_AGENT:
        print("Set EDGAR_USER_AGENT to your real name + email before running (SEC requires this).")
        sys.exit(1)

    df = pd.read_csv(input_csv, parse_dates=["date"])
    ticker_to_cik = load_ticker_to_cik()
    cik_filing_cache = {}

    flags, days_since_list = [], []
    for _, row in df.iterrows():
        ticker = str(row["symbol"]).upper()
        cik = ticker_to_cik.get(ticker)
        if cik is None:
            flags.append(0)
            days_since_list.append(DAYS_SINCE_STALE_CAP + 1)
            continue
        eightk_dates = get_8k_filing_dates(cik, cik_filing_cache)
        flag, bucketed = compute_catalyst_fields(row["date"], eightk_dates)
        flags.append(flag)
        days_since_list.append(bucketed)
        time.sleep(0.11)  # SEC's stated fair-use limit is 10 requests/second

    df["catalyst_flag"] = flags
    df["days_since_catalyst"] = days_since_list
    df.to_csv(output_csv, index=False)
    print(f"Wrote {output_csv} with catalyst_flag / days_since_catalyst for {len(df)} rows")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python sec_edgar_catalyst_flag.py <input_csv> [output_csv]")
        sys.exit(1)
    main(*sys.argv[1:])
