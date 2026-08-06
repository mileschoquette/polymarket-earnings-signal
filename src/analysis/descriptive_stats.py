"""Descriptive stats on the earnings panel: coverage over time, EPS/probability distributions,
realized beat rates, a price-history liquidity proxy, and the historical beat-rate baseline itself.
"""
import json
from pathlib import Path

import pandas as pd

PRICE_HISTORY_DIR = Path(__file__).resolve().parents[2] / "data" / "raw" / "polymarket" / "price_history"


def sample_coverage_by_quarter(df):
    """Events and unique tickers per calendar quarter of scheduled_date."""
    quarter = pd.to_datetime(df["scheduled_date"]).dt.to_period("Q")
    return df.groupby(quarter).agg(n_events=("event_id", "size"), n_unique_tickers=("ticker", "nunique"))


def eps_and_prob_summary(df):
    """Mean/std/min/quartiles/max for consensus_eps and implied_prob_pre_earnings."""
    return df[["consensus_eps", "implied_prob_pre_earnings"]].describe()


def realized_beat_rate_overall(df):
    """Overall mean of actual_beat across all events."""
    return df["actual_beat"].mean()


def beat_rate_by_sector(df):
    """Mean actual_beat and event count per sector (non-null sector only), sorted descending by beat rate."""
    sectored = df[df["sector"].notna()]
    out = sectored.groupby("sector").agg(beat_rate=("actual_beat", "mean"), n_events=("actual_beat", "size"))
    return out.sort_values("beat_rate", ascending=False)


def history_point_count(price_history):
    """Number of {t, p} points in one event's price-history dict, our liquidity/data-density proxy
    (Polymarket's price-history payload has no volume field, only timestamped price ticks)."""
    return len(price_history.get("history", []))


def liquidity_by_quarter(df, price_history_dir=PRICE_HISTORY_DIR):
    """Mean/median number of price-history points per event, grouped by scheduled_date quarter."""
    counts = []
    for event_id in df["event_id"]:
        path = price_history_dir / f"{event_id}.json"
        if not path.exists():
            continue
        counts.append({"event_id": event_id, "n_points": history_point_count(json.loads(path.read_text()))})
    counts_df = pd.DataFrame(counts).merge(df[["event_id", "scheduled_date"]], on="event_id")
    quarter = pd.to_datetime(counts_df["scheduled_date"]).dt.to_period("Q")
    return counts_df.groupby(quarter)["n_points"].agg(["mean", "median", "count"])


def historical_beat_rate_summary(df):
    """Mean/std/min/quartiles/max for historical_beat_rate, the shrinkage-based baseline."""
    return df["historical_beat_rate"].describe()
