# Trading Strategy Research Project

Two tracks, both mid-research, neither validated yet.

## 01-forex-session-sweep/
The original Asia/London session liquidity-sweep + FVG reversal strategy on forex.
- `session-sweep-fvg-strategy.md` — the full playbook/rules
- `automating-session-sweep-strategy.md` — automation architecture (n8n/TradingView/OANDA)
- `backtest_session_sweep_fvg.py` — starter backtest using backtesting.py + OANDA data (UNTESTED, has known gaps listed at the bottom of the file)
- `test_oanda_connection.py` — minimal script to verify your OANDA API token works before running the full backtest

Research verdict so far: the near-identical setup was tested independently on futures data and came back with a statistically significant NEGATIVE edge after realistic costs. Treat this track skeptically until your own backtest says otherwise.

## 02-low-float-track/
A math-driven redesign: instead of discretionary ICT-style pattern reading, statistically test whether float size, gap %, RVOL, and a binary catalyst flag actually predict fade-vs-continuation on low-float stock gaps.
- `claude-code-brief-low-float-gap-sweep.md` — the full project spec, read this first
- `quantconnect_phase1_data_pull.py` — QuantConnect Research notebook. The two flagged blockers from the brief's task list are fixed (point-in-time `CompanyProfile.SharesOutstanding` field confirmed against QC's docs; QC500 placeholder replaced with `qb.GetFundamental(d)` for all-US-equities, survivorship-bias-free coverage), and RVOL / ATR-normalized-gap are now computed properly instead of stubbed. **Still not run against a live QC account from this environment** (QC's domain isn't reachable here) — run it in an actual Research notebook and sanity-check the candidate count/field values before trusting it, per the brief.
- `sec_edgar_catalyst_flag.py` — new: self-sourced, free 8-K catalyst_flag / days_since_catalyst via SEC EDGAR's public submissions API, joined onto the QC output. Set `EDGAR_USER_AGENT` before running (SEC requires it). Documents an explicit precision caveat (filing-date-only, not filing-time) in its own docstring.
- `phase1_analysis.py` — new: outcome_label computation (with its dependency on an as-yet-unbuilt `price_after_lookahead` field flagged explicitly, not faked), conditional probability tables by float/gap/RVOL/catalyst bucket, chi-square + logistic regression significance testing with Bonferroni correction, and a chronological 70/30 in-sample/out-of-sample split — per the brief's validation standard.
- `requirements.txt` — local dependencies for `sec_edgar_catalyst_flag.py` and `phase1_analysis.py` (the QC pull itself only runs inside QuantConnect's cloud notebook).

**Not yet done, still requires a human with QC/EDGAR access:** actually running the QC notebook end-to-end, verifying the 100+ event sample size, and adding the `price_after_lookahead` field the outcome_label calculation depends on.

## Suggested first prompt to Claude Code
"Read README.md, then read 02-low-float-track/claude-code-brief-low-float-gap-sweep.md in full. Start on its 'First Session Task List' — treat quantconnect_phase1_data_pull.py as an untested draft that needs debugging, not working code."
