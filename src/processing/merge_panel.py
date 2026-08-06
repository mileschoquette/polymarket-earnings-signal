"""Combine per-event features with stock-price reactions and firm metadata into one earnings panel.

One row per event with a resolved outcome (per build_features): ticker/date/consensus features,
the pre/post-earnings return in the underlying stock, and static firm metadata.
"""
import json
from pathlib import Path

import pandas as pd

from src.processing.build_features import build_features

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
EVENTS_DIR = DATA_DIR / "raw" / "polymarket" / "events"
PRICE_HISTORY_DIR = DATA_DIR / "raw" / "polymarket" / "price_history"
YFINANCE_DIR = DATA_DIR / "raw" / "yfinance"
OUT_PATH = DATA_DIR / "processed" / "earnings_panel.parquet"

_price_cache = {}
_meta_cache = {}


def _load_closes(ticker):
    """Cached daily close series for a ticker, or None if its yfinance parquet is missing."""
    if ticker not in _price_cache:
        path = YFINANCE_DIR / f"{ticker}.parquet"
        _price_cache[ticker] = pd.read_parquet(path)["Close"] if path.exists() else None
    return _price_cache[ticker]


def _load_meta(ticker):
    """Cached {sector, industry, marketCap} for a ticker, all-None if its _meta.json is missing."""
    if ticker not in _meta_cache:
        path = YFINANCE_DIR / f"{ticker}_meta.json"
        meta = json.loads(path.read_text()) if path.exists() else {}
        _meta_cache[ticker] = {k: meta.get(k) for k in ("sector", "industry", "marketCap")}
    return _meta_cache[ticker]


def stock_reaction(ticker, scheduled_date):
    """price_t_minus_1/t_plus_1/t_plus_5 (last close strictly before, and 1st/5th close strictly
    after, scheduled_date) and the returns off t_minus_1. scheduled_date itself is excluded from
    both sides since we don't know whether the announcement was before-open or after-close, so its
    close is a mixed/ambiguous partial reaction, not a clean pre- or post-earnings price. Any field
    left None if unavailable (missing parquet, or scheduled_date outside the ticker's pulled range).
    """
    result = {"price_t_minus_1": None, "price_t_plus_1": None, "price_t_plus_5": None,
              "return_t_plus_1": None, "return_t_plus_5": None}
    closes = _load_closes(ticker)
    if closes is None:
        return result

    target = pd.Timestamp(scheduled_date)
    if closes.index.tz is not None:
        target = target.tz_localize(closes.index.tz)

    before = closes[closes.index < target]
    after = closes[closes.index > target]
    if before.empty:
        return result

    p_minus_1 = before.iloc[-1]
    result["price_t_minus_1"] = p_minus_1
    if len(after) >= 1:
        result["price_t_plus_1"] = after.iloc[0]
        result["return_t_plus_1"] = after.iloc[0] / p_minus_1 - 1
    if len(after) >= 5:
        result["price_t_plus_5"] = after.iloc[4]
        result["return_t_plus_5"] = after.iloc[4] / p_minus_1 - 1
    return result


def main():
    events = {p.stem: json.loads(p.read_text()) for p in EVENTS_DIR.glob("*.json")}
    price_histories = {p.stem: json.loads(p.read_text()) for p in PRICE_HISTORY_DIR.glob("*.json")}
    features_by_event = build_features(events, price_histories)

    rows = []
    for event_id, feat in features_by_event.items():
        ticker = feat["ticker"]
        row = {"event_id": event_id, **feat}
        row.update(stock_reaction(ticker, feat["scheduled_date"]))
        row.update(_load_meta(ticker))
        rows.append(row)
    df = pd.DataFrame(rows)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT_PATH)

    n = len(df)
    print(f"total rows: {n}")
    for col in ("return_t_plus_1", "return_t_plus_5"):
        cov = df[col].notna().sum()
        print(f"{col}: {cov}/{n} non-null ({100 * cov / n:.1f}%)")
    print()
    print(df.dtypes)


if __name__ == "__main__":
    main()
