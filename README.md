# Kalshi Trading Signal

Research project: do Kalshi (CFTC-regulated event-contract exchange) prices carry information
not yet reflected in financial markets, and is it systematically tradable?

Core sample is Kalshi's macro contracts (FOMC, CPI, jobs reports), which have traded since ~2021
and have a direct academic precedent (Diercks, Katz & Wright, "Kalshi and the Rise of Macro
Markets," Federal Reserve FEDS working paper, Feb 2026, SSRN 6333085). The Palantir earnings
anecdote that motivated this project is kept as a small, isolated illustrative case study — Kalshi's
single-stock earnings markets are too new to support a real backtest.

Full plan: `/Users/mileschoquette/.claude/plans/a-couple-days-ago-twinkly-wolf.md`.

## Setup
```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in FRED_API_KEY
```

## Pipeline order
1. `src/ingestion/pull_kalshi_series.py` — pull Kalshi market history per category
2. `src/ingestion/pull_yfinance.py`, `pull_fred.py` — comparison data
3. `src/processing/collapse_bucket_market.py` → `build_event_windows.py` → `merge_panel.py`
4. `src/analysis/` — descriptive stats, calibration, encompassing regression, lead-lag
5. `src/strategy/` — signal, backtest, performance
6. `notebooks/` — one notebook per stage, drives the actual runs and plots
