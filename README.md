# Polymarket Earnings Signal

Research project: does Polymarket's recurring "Will [company] beat quarterly earnings?" market
(tag_id 1013) carry information about earnings surprises beyond what a firm's own historical beat
rate already predicts, and is that edge systematically tradable?

The motivating anecdote (~93% odds Palantir would beat earnings, followed by a 30% stock pop) was
originally misattributed to Kalshi; that market was actually on Polymarket. Kalshi's own
Palantir-related products are customer-count KPI markets and earnings-call word-mention markets,
not beat/miss probability contracts. Polymarket runs the beat/miss product systematically: 1,231
resolved events from June 2025 through August 2026 (the tag's very earliest event, a January 2024
"MrBeast Twitter earnings" market, is an unrelated mistagged post, not a real earnings-beat market)
across roughly 415 tickers, each with a consensus EPS estimate and a full implied-probability price
history.

The design: build a no-look-ahead, firm-specific historical beat-rate baseline for each event, then
test whether Polymarket's implied probability beats that baseline (calibration, encompassing
regression), whether the stock's own pre-announcement price action anticipates the market's signal
(event study), and whether any informational edge survives as a backtested trading strategy once
same-day earnings clustering is properly accounted for in the significance testing.

## Results

Polymarket's implied probability is well-calibrated and beats the firm-history baseline decisively:
a lower Brier score (0.149 vs. 0.185, 90% bootstrap CI on the gap excludes zero) and a large,
highly significant coefficient (5.78, p < 10⁻³⁵) in a logistic encompassing regression that survives
three different clustering-robust inference procedures. Neither the market's short-run momentum nor
the stock's own pre-announcement price reaction adds anything beyond that — two consistent null
results. A volatility-targeted trading strategy built on the market/firm-history divergence beats
buy-and-hold and firm-history-only benchmarks in-sample at both a 1-day and 5-day exit horizon, but
three independent significance tests (permutation, block bootstrap, Jobson-Korkie) all fail to
distinguish that edge from noise once same-day earnings clustering collapses the effective sample
to roughly 181 independent trading dates. The market's price is genuinely informative; whether that
translates into a confirmed trading edge remains open pending a longer sample.

Full writeup: [`paper/draft.pdf`](paper/draft.pdf) (source: [`paper/draft.md`](paper/draft.md)).

## Setup
```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```
No API keys needed — Polymarket's Gamma and CLOB APIs and yfinance are all unauthenticated.

## Project structure
- `src/polymarket_client/` — thin Gamma/CLOB API client with rate-limit-aware backoff
- `src/ingestion/` — pulls and caches raw Polymarket events, price histories, and yfinance stock data
- `src/processing/` — parses raw contract text, builds no-look-ahead features, merges the analysis panel
- `src/analysis/` — descriptive stats, calibration, encompassing regression, event-reaction (CAR)
- `src/strategy/` — signal construction, backtest, benchmarks, performance, significance testing
- `notebooks/` — one driver script per analysis stage; runs the pipeline and saves `paper/figures/`
- `tests/` — pytest suite (62 tests) covering parsing, feature no-look-ahead guarantees, and every
  analysis/strategy module
- `data/` — raw API caches (gitignored, regenerate via `src/ingestion/`) and the processed panel
- `paper/` — the write-up and its figures
- `config/earnings_config.yaml` — API endpoints, pipeline parameters, backtest settings

## Pipeline order
1. `src/ingestion/pull_earnings_events.py` — enumerate all Earnings-tag events
2. `src/processing/parse_market_fields.py` — extract ticker/basis/date/consensus from contract text
3. `src/ingestion/pull_price_history.py`, `pull_yfinance_reactions.py` — implied-prob path + stock reaction
4. `src/processing/build_features.py` → `merge_panel.py` → `data/processed/earnings_panel.parquet`
5. `src/analysis/` — descriptive stats, calibration, encompassing regression, event-reaction (CAR)
6. `src/strategy/` — signal, backtest, performance, significance
7. `notebooks/` — one notebook per stage, drives the actual runs and plots

## Tests
```
pytest -q
```
62 tests, including a dedicated no-look-ahead invariant test for the feature-building pipeline.

## License
MIT — see [LICENSE](LICENSE).
