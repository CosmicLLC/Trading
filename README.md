# Trading Strategy Research Project

Focus: the low-float gap sweep track. The earlier forex session-sweep track
(`01-forex-session-sweep/`) is deprioritized/ignored — prior research on a
near-identical setup came back with a statistically significant NEGATIVE edge
on futures data after realistic costs, so it's not worth pursuing right now.

## 02-low-float-track/
A math-driven redesign: instead of discretionary ICT-style pattern reading, statistically test whether float size, gap %, RVOL, and a binary catalyst flag actually predict fade-vs-continuation on low-float stock gaps.
- `claude-code-brief-low-float-gap-sweep.md` — the full project spec, read this first
- `quantconnect_phase1_data_pull.py` — QuantConnect Research notebook. The two flagged blockers from the brief's task list are fixed (point-in-time `CompanyProfile.SharesOutstanding` field confirmed against QC's docs; QC500 placeholder replaced with `qb.GetFundamental(d)` for all-US-equities, survivorship-bias-free coverage), RVOL / ATR-normalized-gap are computed properly instead of stubbed, and `price_after_lookahead` (regular-session price `FADE_LOOKAHEAD_MINUTES` after the open) is now included so `phase1_analysis.py` can compute real outcome labels. **Still not run against a live QC account from this environment** (QC's domain isn't reachable here) — run it in an actual Research notebook and sanity-check the candidate count/field values before trusting it, per the brief.
- `sec_edgar_catalyst_flag.py` — self-sourced, free 8-K catalyst_flag / days_since_catalyst via SEC EDGAR's public submissions API, joined onto the QC output. Set `EDGAR_USER_AGENT` before running (SEC requires it). Documents an explicit precision caveat (filing-date-only, not filing-time) in its own docstring.
- `phase1_analysis.py` — outcome_label computation, conditional probability tables by float/gap/RVOL/catalyst bucket, chi-square + logistic regression significance testing with Bonferroni correction, and a chronological 70/30 in-sample/out-of-sample split — per the brief's validation standard. `FADE_LOOKAHEAD_MINUTES` here must match the same constant in `quantconnect_phase1_data_pull.py`.
- `requirements.txt` — local dependencies for `sec_edgar_catalyst_flag.py` and `phase1_analysis.py` (the QC pull itself only runs inside QuantConnect's cloud notebook).

**Not yet done, still requires a human with QC/EDGAR access:** actually running the QC notebook end-to-end in a live QuantConnect Research environment, verifying the 100+ event sample size, and sanity-checking field values (shares outstanding, universe size) against known low-float names.

## Suggested next step
Run `quantconnect_phase1_data_pull.py` cell-by-cell in a QuantConnect Research notebook. Confirm `CompanyProfile.SharesOutstanding` returns non-null values and `qb.GetFundamental(d)` returns thousands of candidates per date (not ~500). Paste back any errors for debugging.
