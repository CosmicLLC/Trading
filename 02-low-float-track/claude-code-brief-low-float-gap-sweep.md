# Project Brief: Low-Float Gap Sweep — Statistical Edge Analysis

## Context for the agent picking this up

This project replaces a discretionary "read the chart" trading approach with a quantitative one. The original idea came from ICT/Smart Money Concepts retail trading style (session liquidity sweeps, fair value gaps), which prior research determined has **no rigorous published evidence of a real edge** and is largely narrative dressed up as pattern recognition. Rather than abandon the underlying concept, we are testing whether a *mathematically defined* version of it holds up: does a pre-market high/low sweep on a low-float stock predict a statistically real fade or continuation, once we control for objective variables?

**Guiding principle for all work on this project: no discretionary judgment, no narrative interpretation, no sentiment reading. Every input must be a number or a binary flag that can be computed identically by two different people (or two different code runs) from the same raw data. If a step requires "does this look clean" or "does this news feel significant," it does not belong in this system — reduce it to a measurable proxy or drop it.**

This is Phase 1 of a two-track project. Track A (this document) is low-float equity gap sweeps. Track B (separate, later) is a similar statistical approach applied to thin/illiquid CME futures contracts (overnight range sweeps). Do not start Track B until Track A's Phase 1 analysis is complete.

---

## The Hypothesis Being Tested

**Null hypothesis:** Whether a pre-market high/low sweep on a low-float stock fades vs. continues is not meaningfully predictable from float size, relative volume, gap size, or catalyst presence — i.e., any apparent pattern is noise.

**What we're actually checking first (before any trading rule):** whether specific objective variables (below) statistically separate "swept and faded" from "swept and continued" outcomes, using a survivorship-bias-free historical dataset.

Do not build entry/exit trading logic yet. Phase 1 is pure statistical characterization of the phenomenon, not strategy construction.

---

## Data Requirements — Read This Before Sourcing Anything

**Critical constraint #1: the dataset must be survivorship-bias-free.** Most free/cheap historical US equity data (Yahoo Finance, most free APIs) only includes tickers that are still listed today, silently excluding every stock that was delisted, halted permanently, went to zero, or was acquired. For low-float/penny stocks specifically, this is a large fraction of the actual population, and using survivor-only data will produce a falsely optimistic result — this is exactly the kind of bad data problem this project exists to eliminate.

**Critical constraint #2, discovered during vendor research: the dataset must include intraday/pre-market bars, not daily-only data.** Norgate Data and Sharadar were both evaluated and ruled out as the primary price source — both are explicitly EOD/daily-only with no intraday data at all, which makes them structurally incapable of detecting a pre-market high/low sweep. Do not use either as the sole price source. Sharadar may still be useful narrowly for shares-outstanding data (see below).

**Primary data source: QuantConnect Research Environment, using the Algoseek US Equities dataset.**
- Free tier gives up to ~1 year of history with no credit card, via QuantConnect's cloud Research Notebook (`qb = QuantBook()`). Use this to prototype and partially validate Phase 1 before spending money on anything.
- Survivorship-bias-free back to 1998/2007 depending on source, includes delisted securities, minute-resolution bars, pre-market data available by adding equities with `extendedMarketHours=True`.
- **Unresolved known gap: Algoseek's QuantConnect dataset explicitly excludes OTC (pink sheet/OTCQB) trades.** Many true low-float microcaps trade OTC rather than Nasdaq/NYSE. Before trusting Phase 1 results, verify the resulting candidate universe still produces a statistically sufficient sample (100+ qualifying events) using only Nasdaq/NYSE-listed low-float names. If the sample is too thin, fall back to an OTC-inclusive paid vendor — FirstRate Data was identified as a candidate (1-minute bars including pre/post-market, 7,000+ delisted tickers, explicit OTC exchange coverage; verify current pricing directly before committing).
- A starter notebook (`quantconnect_phase1_data_pull.py`) already exists implementing this pull. **It is untested against a live QuantConnect account** and has known placeholder issues flagged directly in its own comments — most importantly, it uses a "QC500" universe as a placeholder, which is a curated large-cap list that will likely exclude most real low-float microcaps. This must be swapped for a true all-US-equities historical universe call before any output from it is trustworthy. Also unverified: the exact field name for point-in-time shares outstanding in QuantConnect's Fundamental object (flagged in-line in the notebook as needing verification against QC's docs).
- Data needed regardless of source: daily OHLCV plus pre-market session high/low, and **shares outstanding / float history** (use the value as of the date in question, not today's value, or you introduce look-ahead bias).

**Fallback / supplementary source: Sharadar** (sharadar.com or Nasdaq Data Link). Tiered pricing (~$9/mo Prices, ~$19/mo Fundamentals, ~$29/mo Bundle — verify current pricing). Use the Fundamentals tier specifically if QuantConnect's Fundamental data doesn't cleanly yield point-in-time shares outstanding. It also bundles a "Material Corporate Events" table from SEC 8-K filings — though this can be self-sourced for free instead (see below), so don't pay for Fundamentals for that reason alone.

**Additional data needed:**
- A catalyst flag source. **Decision: self-source this for free from SEC EDGAR's 8-K filing index** rather than paying for a vendor's pre-packaged version — the underlying data is the same public filing, and EDGAR's full-text search/filing index is free to query. A binary "was there a same-day or prior-evening 8-K filing" flag is sufficient. This is intentionally minimal — no sentiment analysis, just presence/absence of a trigger.

---

## Variable Definitions (all must be computed identically, no subjective interpretation)

| Variable | Definition | Type |
|---|---|---|
| `float_shares` | Public float as of the trading date (not current) | Continuous |
| `rvol` | Day's pre-market or opening volume ÷ that stock's trailing 20-day average volume for the same time-of-day window | Continuous ratio |
| `gap_pct` | (Pre-market high − prior regular-session close) ÷ prior close, as a percentage | Continuous |
| `atr_normalized_gap` | `gap_pct` ÷ the stock's 14-day ATR (as a percentage of price) — this normalizes gap size against the stock's own typical volatility | Continuous |
| `catalyst_flag` | 1 if an identifiable news/press-release/8-K event occurred within the prior 16 hours, else 0 | Binary |
| `days_since_catalyst` | 0 = day of catalyst, 1 = day after, 2 = two days after, etc. Cap at a reasonable max (e.g., 5) and bucket beyond that as "stale" | Categorical/ordinal |
| `sweep_session_time` | Timestamp (market open, or specific minute) the pre-market high/low was swept | Timestamp, used for time-of-day bucketing only |
| `outcome_label` | 1 if price faded back through a defined threshold after the sweep (e.g., closed the next N minutes below the pre-market low after sweeping it, adjust definition and document it explicitly), 0 if it continued past the sweep level | Binary target |

**The exact numeric thresholds for `outcome_label` (how far it must fade/continue, and over what time window, to count) need to be decided and hard-coded explicitly — pick reasonable defaults, document them in the code, and treat them as a parameter to sensitivity-test later, not a fixed truth.**

---

## Phase 1 Deliverable: Base Rate Analysis (no trading rules yet)

1. Build the dataset: pull 2-3 years of low-float gap days. Define "low-float" and "gap day" thresholds explicitly as parameters at the top of the script (e.g., float < 20M shares, gap_pct > 10%) — these are starting points, not fixed truths, and should be easy to adjust.
2. For each qualifying day, compute all variables above and the outcome label.
3. Produce **conditional probability tables**: fade rate sliced by float-size buckets, by gap-size buckets, by RVOL buckets, by catalyst_flag, and by days_since_catalyst. No trading logic — just: "of days matching X condition, what % faded vs. continued."
4. Run a basic statistical significance check on the differences between buckets (chi-square test for categorical splits, or logistic regression treating `outcome_label` as the dependent variable and the continuous variables as predictors — statsmodels' `Logit` is fine for this).
5. Report: which variables, if any, show a statistically significant relationship (p < 0.05, and note this will need correction for multiple comparisons since we're testing several variables — Bonferroni or similar) with the outcome, and what the effect size actually looks like (not just "significant" but "how much does it move the probability").

**This phase produces no automation and places no trades.** The deliverable is a report/notebook showing whether there is any real mathematical signal here at all, before a single line of strategy code gets written.

---

## Explicit Exclusions (do not implement these, even if they seem helpful)

- No sentiment scoring of news content — catalyst is binary presence/absence only.
- No discretionary "quality" scoring of setups.
- No ICT/SMC terminology or concepts (fair value gap, market structure shift, order block) — if a similar concept is genuinely useful, redefine it as one of the objective variables above instead of importing the vocabulary.
- No live trading, paper trading, or order execution in this phase.

---

## Tech Stack

- QuantConnect Research Environment (cloud Jupyter notebook, `QuantBook` API) for the primary price/pre-market data pull — free tier, no local setup needed for this piece
- Python, pandas for data wrangling
- `statsmodels` for the logistic regression / significance testing (preferred over scikit-learn for this phase specifically because we want interpretable coefficients and p-values, not just predictive accuracy)
- `requests` + SEC EDGAR's free filing index API for the 8-K catalyst flag (self-sourced, no paid vendor)
- Sharadar's Python API/REST endpoint only if it turns out to be needed for shares-outstanding data (fallback, not default)
- Jupyter notebook is fine and preferred for Phase 1 — this is exploratory statistical work, not production code yet

## First Session Task List (what to actually do first)

1. Open `quantconnect_phase1_data_pull.py` and treat it as a rough draft, not working code. Walk through it cell by cell in an actual QuantConnect Research notebook.
2. Fix the two flagged issues before anything else: (a) find the correct point-in-time shares-outstanding field in QC's Fundamental data, (b) replace the "QC500" placeholder universe with a true historical all-US-equities screen.
3. Once the universe/float screen is fixed, run it against a small date range first (a month, not years) and sanity-check the candidate list against 5-10 low-float gap days you can verify manually. Do not scale up until this passes.
4. Only after step 3 passes: extend to the full 2-3 year window, add the SEC EDGAR catalyst flag join, and build the outcome_label logic.
5. Check the resulting sample size (target 100+ events) before running any statistical test. If it's too thin because of the OTC exclusion, stop and flag it — that's the trigger to evaluate FirstRate Data as a paid fallback, not a reason to loosen the float/gap thresholds just to get more rows.

## Validation Standard (carried over from prior work on this project — apply here too)

- Minimum 100+ qualifying events before drawing any conclusion from a bucket.
- Split data by time (not randomly) — e.g., tune/explore on the first 70% chronologically, confirm findings hold on the untouched final 30%.
- Report year-by-year base rates, not just the aggregate — a pattern driven by one unusual year (e.g., a single meme-stock mania period) is not a real, persistent effect.
- Correct for multiple comparisons given several variables are being tested simultaneously.

## Next Steps After Phase 1 (do not start yet)

If and only if Phase 1 finds a statistically significant, economically meaningful, year-stable relationship: proceed to Phase 2 (building actual entry/exit rules with realistic execution cost modeling — low-float stocks have wide spreads and heavy slippage risk that must be modeled explicitly, not assumed away). If Phase 1 finds nothing significant or the effect doesn't survive out-of-sample/year-stability checks, that is a valid and useful conclusion — report it plainly rather than searching for a variable combination that "works."
