# Kalshi Trading Signal — project conventions

Despite the folder name, this project studies **Polymarket's** recurring "Will [company] beat
quarterly earnings?" markets (tag_id 1013), not Kalshi — Kalshi doesn't offer per-company
earnings-beat contracts (confirmed against its live API). Research question: does Polymarket's
implied beat probability (and its pre-print trajectory) carry information about earnings
surprises beyond what a firm's own historical beat rate already predicts, and is that tradable?
See `/Users/mileschoquette/.claude/plans/a-couple-days-ago-twinkly-wolf.md` for the full plan.

## Conventions
- All timestamps stored and reasoned about in US/Eastern, converted at ingestion time.
- Files under `data/raw/` are immutable once written. Fix bugs in `src/processing/`, not by editing raw JSON.
- Every module in `src/` has one narrow responsibility. Don't merge ingestion, processing, and analysis steps.
- No look-ahead: the historical beat-rate baseline for event *i* must only use ticker's prior, already-resolved events. This is a specifically tested invariant (`tests/test_build_features.py`), not just a guideline.
