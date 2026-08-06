"""Read-only diagnostic over the full raw dataset: parseability, price bounds, timestamp
ordering, ticker/date dedup, resolution completeness, yfinance/price-history coverage, and
empty price histories. Prints a pass/fail report; fixes nothing.
"""
import json
from collections import defaultdict
from pathlib import Path

from src.processing.parse_market_fields import parse_market

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
EVENTS_DIR = DATA_DIR / "polymarket" / "events"
PRICE_DIR = DATA_DIR / "polymarket" / "price_history"
YFINANCE_DIR = DATA_DIR / "yfinance"


def check_parseability(events):
    """Run parse_market() on every event; return (parsed dict keyed by event_id, list of failed event_ids)."""
    parsed, failed = {}, []
    for event_id, event in events.items():
        result = parse_market(event)
        if result is None:
            failed.append(event_id)
        else:
            parsed[event_id] = result
    return parsed, failed


def check_price_bounds(price_histories):
    """Return list of (event_id, t, p) for any point outside [0, 1]."""
    violations = []
    for event_id, ph in price_histories.items():
        for point in ph.get("history", []):
            p = point.get("p")
            if p is None or not (0 <= p <= 1):
                violations.append((event_id, point.get("t"), p))
    return violations


def check_timestamp_ordering(price_histories):
    """Return list of event_ids whose history 't' values are not non-decreasing."""
    unsorted_files = []
    for event_id, ph in price_histories.items():
        ts = [point["t"] for point in ph.get("history", [])]
        if any(ts[i] > ts[i + 1] for i in range(len(ts) - 1)):
            unsorted_files.append(event_id)
    return unsorted_files


def check_dedup(parsed):
    """Return dict of (ticker, scheduled_date) -> list of event_ids, for pairs with >1 event."""
    groups = defaultdict(list)
    for event_id, fields in parsed.items():
        groups[(fields["ticker"], fields["scheduled_date"])].append(event_id)
    return {k: v for k, v in groups.items() if len(v) > 1}


def check_resolution_completeness(events):
    """Return list of (event_id, outcomePrices) for closed markets with an ambiguous/missing outcome."""
    ambiguous = []
    definitive = ({"1", "0"}, {"0", "1"})
    for event_id, event in events.items():
        markets = event.get("markets") or []
        if not markets:
            continue
        market = markets[0]
        if market.get("closed") is not True:
            continue
        raw = market.get("outcomePrices")
        outcome_ok = False
        if raw:
            try:
                prices = json.loads(raw) if isinstance(raw, str) else raw
                outcome_ok = list(prices) in (["1", "0"], ["0", "1"])
            except (json.JSONDecodeError, TypeError):
                outcome_ok = False
        if not outcome_ok:
            ambiguous.append((event_id, raw))
    return ambiguous


def check_coverage(parsed):
    """Return list of (event_id, ticker) missing a price-history file and/or a yfinance parquet file."""
    gaps = []
    for event_id, fields in parsed.items():
        ticker = fields["ticker"]
        has_price_history = (PRICE_DIR / f"{event_id}.json").exists()
        has_yfinance = (YFINANCE_DIR / f"{ticker}.parquet").exists()
        if not (has_price_history and has_yfinance):
            gaps.append((event_id, ticker, has_price_history, has_yfinance))
    return gaps


def check_empty_history(price_histories):
    """Return list of event_ids whose history list has zero points."""
    return [event_id for event_id, ph in price_histories.items() if len(ph.get("history", [])) == 0]


def main():
    events = {p.stem: json.loads(p.read_text()) for p in EVENTS_DIR.glob("*.json")}
    price_histories = {p.stem: json.loads(p.read_text()) for p in PRICE_DIR.glob("*.json")}

    print(f"Loaded {len(events)} events, {len(price_histories)} price-history files.\n")

    # 1. Parseability
    parsed, failed = check_parseability(events)
    print("=== 1. Parseability ===")
    print(f"{len(parsed)}/{len(events)} events parsed successfully, {len(failed)} returned None.")
    if failed:
        print(f"Failed event_ids: {failed}")
    print()

    # 2. Price bounds
    bound_violations = check_price_bounds(price_histories)
    print("=== 2. Price bounds ===")
    print(f"{len(bound_violations)} out-of-range points found.")
    for event_id, t, p in bound_violations[:10]:
        print(f"  event_id={event_id} t={t} p={p}")
    print()

    # 3. Timestamp ordering
    unsorted_files = check_timestamp_ordering(price_histories)
    print("=== 3. Timestamp ordering ===")
    print(f"{len(unsorted_files)} price-history files with non-monotonic 't'.")
    if unsorted_files:
        print(f"  event_ids: {unsorted_files[:10]}")
    print()

    # 4. Dedup
    dupes = check_dedup(parsed)
    print("=== 4. Dedup (ticker, scheduled_date) ===")
    print(f"{len(dupes)} duplicate (ticker, scheduled_date) pairs found.")
    for key, event_ids in list(dupes.items())[:15]:
        print(f"  {key}: {event_ids}")
    print()

    # 5. Resolution completeness
    ambiguous = check_resolution_completeness(events)
    print("=== 5. Resolution completeness ===")
    print(f"{len(ambiguous)} closed events with ambiguous/missing outcomePrices.")
    for event_id, raw in ambiguous[:10]:
        print(f"  event_id={event_id} outcomePrices={raw!r}")
    print()

    # 6. Coverage
    gaps = check_coverage(parsed)
    missing_tickers = sorted({ticker for _, ticker, has_ph, has_yf in gaps if not has_yf})
    print("=== 6. Coverage (price history + yfinance) ===")
    print(f"{len(gaps)}/{len(parsed)} parsed events missing price-history and/or yfinance data.")
    print(f"Distinct tickers missing yfinance data: {missing_tickers}")
    for event_id, ticker, has_ph, has_yf in gaps[:15]:
        print(f"  event_id={event_id} ticker={ticker} has_price_history={has_ph} has_yfinance={has_yf}")
    print()

    # 7. Empty price history
    empty = check_empty_history(price_histories)
    print("=== 7. Empty price histories ===")
    print(f"{len(empty)} price-history files with zero points.")
    if empty:
        print(f"  event_ids: {empty[:15]}")
    print()

    # Final summary
    print("=== SUMMARY ===")
    print(f"Total events: {len(events)}")
    print(f"Parse success rate: {len(parsed)}/{len(events)} ({100 * len(parsed) / len(events):.2f}%)")
    print(f"Price/timestamp anomalies (checks 2-3): {len(bound_violations)} out-of-range points, {len(unsorted_files)} unsorted files")
    print(f"Duplicate (ticker, scheduled_date) pairs: {len(dupes)}")
    print(f"Resolution-ambiguity count: {len(ambiguous)}")
    print(f"Coverage-gap count: {len(gaps)} events (missing tickers: {missing_tickers})")
    print(f"Empty-history count: {len(empty)}")


if __name__ == "__main__":
    main()
