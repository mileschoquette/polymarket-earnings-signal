# Kalshi Trading Signal — project conventions

Research project testing whether Kalshi (CFTC-regulated event-contract exchange) prices
carry information not yet reflected in financial markets, and whether it's tradable.
See `/Users/mileschoquette/.claude/plans/a-couple-days-ago-twinkly-wolf.md` for the full plan.

## Conventions
- All timestamps stored and reasoned about in US/Eastern, converted at ingestion time. Never mix UTC and ET silently.
- Files under `data/raw/` are immutable once written. Never edit them in place; fix bugs in `src/processing/` and rerun.
- Every module in `src/` has one narrow responsibility (a client, one ingestion script, one processing step, one analysis test). Don't merge steps into a monolith.
- No look-ahead: any processing/analysis step must only use data timestamped strictly before the decision point it's modeling.
- Kalshi's single-stock earnings markets (`earnings_case_study`) are kept fully isolated from `data/processed/merged_panel.parquet` and from the backtest/encompassing regression. They're a smoke test and a small illustrative case study only, not part of the statistical core.
