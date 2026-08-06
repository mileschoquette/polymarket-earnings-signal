# Kalshi Trading Signal

Research project: does Polymarket's recurring "Will [company] beat quarterly earnings?" market
(tag_id 1013) carry information about earnings surprises beyond what a firm's own historical beat
rate already predicts, and is that edge systematically tradable?

The motivating anecdote (~93% odds Palantir would beat earnings, followed by a 30% stock pop) was
originally misattributed to Kalshi; that market was actually on Polymarket. Kalshi's own
Palantir-related products are customer-count KPI markets and earnings-call word-mention markets,
not beat/miss probability contracts. Polymarket runs the beat/miss product systematically: 1,228
closed events since January 2024 across hundreds of tickers, each with a consensus EPS estimate
and a full implied-probability price history.

Full plan: `/Users/mileschoquette/.claude/plans/a-couple-days-ago-twinkly-wolf.md`.

## Setup
```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```
No API keys needed — Polymarket's Gamma and CLOB APIs and yfinance are all unauthenticated.

## Pipeline order
1. `src/ingestion/pull_earnings_events.py` — enumerate all Earnings-tag events
2. `src/processing/parse_market_fields.py` — extract ticker/basis/date/consensus from slugs
3. `src/ingestion/pull_price_history.py`, `pull_yfinance_reactions.py` — implied-prob path + stock reaction
4. `src/processing/build_features.py` → `merge_panel.py` → `data/processed/earnings_panel.parquet`
5. `src/analysis/` — descriptive stats, calibration, encompassing regression, event-reaction (CAR)
6. `src/strategy/` — signal, backtest, performance
7. `notebooks/` — one notebook per stage, drives the actual runs and plots
