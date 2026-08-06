"""Per-event features: actual outcome, historical beat-rate baseline, implied-probability
snapshot and momentum. The ticker and global baselines are expanding statistics computed only
from events strictly prior (by scheduled_date, processed one calendar date at a time so same-day
events never leak into each other) to the event being scored — no look-ahead.
"""
import json
from datetime import datetime, timedelta, timezone
from itertools import groupby
from pathlib import Path

import yaml

from src.processing.parse_market_fields import parse_market

_config = yaml.safe_load((Path(__file__).resolve().parents[2] / "config" / "earnings_config.yaml").read_text())
HISTORY_WINDOW = _config["features"]["historical_beat_rate_window"]
MOMENTUM_DAYS = _config["features"]["momentum_window_days"]  # e.g. [5, 1] -> T-5d, T-1d
SHRINKAGE_PRIOR_STRENGTH = 4  # weight of the global backstop in the shrinkage blend, in pseudo-observations


def _actual_beat(event):
    """1 if the market resolved Yes (beat), 0 if No, None if not settled/ambiguous."""
    markets = event.get("markets") or []
    if not markets or markets[0].get("closed") is not True:
        return None
    raw = markets[0].get("outcomePrices")
    try:
        prices = list(json.loads(raw) if isinstance(raw, str) else raw)
    except (TypeError, json.JSONDecodeError):
        return None
    if prices == ["1", "0"]:
        return 1
    if prices == ["0", "1"]:
        return 0
    return None


def _clean_history(history):
    """Dedupe by timestamp and sort (raw data has a known duplicated 'current price' tick in ~2.6% of files)."""
    by_ts = {point["t"]: point["p"] for point in history}
    return sorted(by_ts.items())


def _price_at_or_before(sorted_points, target_ts):
    """Most recent price at or before target_ts, or None if no such point exists. Never returns a later point."""
    result = None
    for t, p in sorted_points:
        if t > target_ts:
            break
        result = p
    return result


def _snapshot_ts(scheduled_date, days_before):
    day = datetime.strptime(scheduled_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int((day - timedelta(days=days_before)).timestamp())


def build_snapshot_features(scheduled_date, price_history):
    """implied_prob_pre_earnings (near snapshot) and implied_prob_momentum (near minus far snapshot)."""
    sorted_points = _clean_history(price_history.get("history", []))
    far_days, near_days = max(MOMENTUM_DAYS), min(MOMENTUM_DAYS)
    p_far = _price_at_or_before(sorted_points, _snapshot_ts(scheduled_date, far_days))
    p_near = _price_at_or_before(sorted_points, _snapshot_ts(scheduled_date, near_days))
    momentum = (p_near - p_far) if (p_far is not None and p_near is not None) else None
    return {"implied_prob_pre_earnings": p_near, "implied_prob_momentum": momentum}


def shrunk_beat_rate(ticker_outcomes, global_outcomes):
    """Blend a ticker's own trailing beat rate with an expanding global backstop, weighted by observation count."""
    n = len(ticker_outcomes)
    global_rate = sum(global_outcomes) / len(global_outcomes) if global_outcomes else 0.5
    if n == 0:
        return global_rate
    ticker_rate = sum(ticker_outcomes) / n
    return (n * ticker_rate + SHRINKAGE_PRIOR_STRENGTH * global_rate) / (n + SHRINKAGE_PRIOR_STRENGTH)


def build_features(events_by_id, price_histories_by_id):
    """{event_id: {ticker, scheduled_date, consensus_eps, actual_beat, historical_beat_rate,
    implied_prob_pre_earnings, implied_prob_momentum}} for every event with a resolved outcome
    and parseable fields. Events without a resolved outcome (still open) or that fail parsing are skipped.
    """
    records = []
    for event_id, event in events_by_id.items():
        parsed = parse_market(event)
        beat = _actual_beat(event)
        if parsed is None or beat is None:
            continue
        records.append({**parsed, "event_id": event_id, "actual_beat": beat})

    records.sort(key=lambda r: r["scheduled_date"])

    ticker_history = {}
    global_history = []
    features_by_event = {}

    for _, day_records in groupby(records, key=lambda r: r["scheduled_date"]):
        day_records = list(day_records)

        for record in day_records:
            ticker = record["ticker"]
            prior_ticker_outcomes = ticker_history.get(ticker, [])[-HISTORY_WINDOW:]
            historical_beat_rate = shrunk_beat_rate(prior_ticker_outcomes, global_history)

            price_history = price_histories_by_id.get(record["event_id"], {"history": []})
            snapshot = build_snapshot_features(record["scheduled_date"], price_history)

            features_by_event[record["event_id"]] = {
                "ticker": ticker,
                "scheduled_date": record["scheduled_date"],
                "consensus_eps": record["consensus_eps"],
                "actual_beat": record["actual_beat"],
                "historical_beat_rate": historical_beat_rate,
                **snapshot,
            }

        # Update state only after scoring every event on this date, so same-day events never leak into each other.
        for record in day_records:
            ticker_history.setdefault(record["ticker"], []).append(record["actual_beat"])
            global_history.append(record["actual_beat"])

    return features_by_event
