"""
Low-Float Gap Sweep — Phase 1 Base Rate Analysis

Input: low_float_gap_with_catalyst.csv (output of sec_edgar_catalyst_flag.py, which
itself consumes low_float_gap_candidates.csv from quantconnect_phase1_data_pull.py).

This is pure statistical characterization -- no trading rules, no entry/exit logic,
per the project brief. Produces conditional probability tables, chi-square /
logistic-regression significance tests with a multiple-comparison correction, and a
chronological (not random) 70/30 split so findings can be checked out-of-sample.

Run locally with: python phase1_analysis.py low_float_gap_with_catalyst.csv
"""

import sys

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency
import statsmodels.api as sm
import statsmodels.formula.api as smf

MIN_EVENTS = 100  # validation standard from the brief -- do not draw conclusions below this
FADE_LOOKAHEAD_MINUTES = 30  # outcome_label window, a parameter to sensitivity-test later


def compute_outcome_label(row):
    """
    outcome_label = 1 (faded) if price closed back below the pre-market low within
    FADE_LOOKAHEAD_MINUTES of the open after sweeping the pre-market high, else 0
    (continued). THRESHOLD IS A DOCUMENTED DEFAULT, NOT GROUND TRUTH -- sensitivity
    test by re-running with different FADE_LOOKAHEAD_MINUTES values once Phase 1
    passes its first check.

    NOTE: this placeholder assumes the upstream data pull is extended to include a
    post-sweep price sample at FADE_LOOKAHEAD_MINUTES after the open -- that field
    (`price_after_lookahead`) does not exist yet in quantconnect_phase1_data_pull.py
    and must be added there before this function produces real labels. Flagging this
    explicitly rather than fabricating a formula that silently returns garbage.
    """
    if "price_after_lookahead" not in row or pd.isna(row.get("price_after_lookahead")):
        return np.nan
    return int(row["price_after_lookahead"] < row["premarket_low"])


def bucket_column(series, edges, labels):
    return pd.cut(series, bins=edges, labels=labels, include_lowest=True)


def conditional_probability_table(df, group_col):
    sub = df.dropna(subset=[group_col, "outcome_label"])
    table = sub.groupby(group_col, observed=True)["outcome_label"].agg(
        n="count", fade_rate="mean"
    )
    return table


def chi_square_test(df, group_col):
    sub = df.dropna(subset=[group_col, "outcome_label"])
    contingency = pd.crosstab(sub[group_col], sub["outcome_label"])
    chi2, p, dof, _ = chi2_contingency(contingency)
    return chi2, p, dof


def bonferroni_correct(p_values, alpha=0.05):
    n = len(p_values)
    return {k: (v, v * n < alpha) for k, v in p_values.items()}


def main(input_csv):
    df = pd.read_csv(input_csv, parse_dates=["date"])
    df = df.sort_values("date")

    df["outcome_label"] = df.apply(compute_outcome_label, axis=1)
    labeled = df.dropna(subset=["outcome_label"])

    print(f"Total candidate rows: {len(df)}")
    print(f"Rows with a computed outcome_label: {len(labeled)}")
    if len(labeled) < MIN_EVENTS:
        print(
            f"STOP: {len(labeled)} labeled events is below the {MIN_EVENTS}-event "
            "minimum from the validation standard. Do not draw conclusions from "
            "buckets below this. Fix the upstream pull (see compute_outcome_label's "
            "docstring) or widen the date range before proceeding."
        )
        return

    # Chronological split, not random -- per validation standard.
    split_idx = int(len(labeled) * 0.7)
    in_sample = labeled.iloc[:split_idx]
    out_of_sample = labeled.iloc[split_idx:]
    print(f"In-sample (first 70%, chronological): {len(in_sample)} events")
    print(f"Out-of-sample (final 30%): {len(out_of_sample)} events")

    # --- Bucketing for conditional probability tables ---
    for frame_name, frame in [("in_sample", in_sample), ("out_of_sample", out_of_sample)]:
        frame = frame.copy()
        frame["float_bucket"] = bucket_column(
            frame["float_shares"] if "float_shares" in frame else pd.Series(np.nan, index=frame.index),
            edges=[0, 5_000_000, 10_000_000, 20_000_000, np.inf],
            labels=["<5M", "5-10M", "10-20M", ">20M"],
        )
        frame["gap_bucket"] = bucket_column(
            frame["gap_pct"], edges=[-np.inf, 10, 25, 50, np.inf], labels=["<10%", "10-25%", "25-50%", ">50%"]
        )
        frame["rvol_bucket"] = bucket_column(
            frame["rvol"], edges=[0, 2, 5, 10, np.inf], labels=["<2x", "2-5x", "5-10x", ">10x"]
        )

        print(f"\n=== {frame_name}: fade rate by float bucket ===")
        print(conditional_probability_table(frame, "float_bucket"))
        print(f"\n=== {frame_name}: fade rate by gap bucket ===")
        print(conditional_probability_table(frame, "gap_bucket"))
        print(f"\n=== {frame_name}: fade rate by RVOL bucket ===")
        print(conditional_probability_table(frame, "rvol_bucket"))
        if "catalyst_flag" in frame:
            print(f"\n=== {frame_name}: fade rate by catalyst_flag ===")
            print(conditional_probability_table(frame, "catalyst_flag"))
        if "days_since_catalyst" in frame:
            print(f"\n=== {frame_name}: fade rate by days_since_catalyst ===")
            print(conditional_probability_table(frame, "days_since_catalyst"))

        # --- Year-by-year base rates, per validation standard ---
        frame["year"] = frame["date"].dt.year
        print(f"\n=== {frame_name}: fade rate by year (checking for single-year-driven effects) ===")
        print(conditional_probability_table(frame, "year"))

    # --- Significance testing (in-sample only, confirm on out-of-sample separately) ---
    p_values = {}
    for col in ["gap_bucket", "rvol_bucket", "catalyst_flag"]:
        frame = in_sample.copy()
        frame["gap_bucket"] = bucket_column(
            frame["gap_pct"], edges=[-np.inf, 10, 25, 50, np.inf], labels=["<10%", "10-25%", "25-50%", ">50%"]
        )
        frame["rvol_bucket"] = bucket_column(
            frame["rvol"], edges=[0, 2, 5, 10, np.inf], labels=["<2x", "2-5x", "5-10x", ">10x"]
        )
        try:
            _, p, _ = chi_square_test(frame, col)
            p_values[col] = p
        except Exception as e:
            print(f"Chi-square failed for {col}: {e}")

    print("\n=== Chi-square p-values (in-sample, uncorrected) ===")
    print(p_values)
    print("\n=== After Bonferroni correction (alpha=0.05) ===")
    print(bonferroni_correct(p_values))

    # --- Logistic regression: outcome_label ~ continuous predictors ---
    reg_cols = [c for c in ["gap_pct", "atr_normalized_gap", "rvol", "catalyst_flag"] if c in in_sample]
    reg_df = in_sample.dropna(subset=reg_cols + ["outcome_label"])
    if len(reg_df) >= MIN_EVENTS and reg_cols:
        formula = "outcome_label ~ " + " + ".join(reg_cols)
        model = smf.logit(formula, data=reg_df).fit(disp=False)
        print("\n=== Logistic regression (in-sample) ===")
        print(model.summary())
        print(
            "\nEffect sizes above are log-odds coefficients -- convert to probability "
            "deltas at representative predictor values before reporting to a human; "
            "do not report 'significant' without also reporting the magnitude."
        )
    else:
        print(f"\nSkipping logistic regression: insufficient complete rows ({len(reg_df)}) or missing columns.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python phase1_analysis.py <low_float_gap_with_catalyst.csv>")
        sys.exit(1)
    main(sys.argv[1])
