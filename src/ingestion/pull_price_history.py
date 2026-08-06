"""Pull implied-probability price history for each parsed earnings event's Yes token."""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from src.polymarket_client import client
from src.processing.parse_market_fields import parse_market

EVENTS_DIR = Path(__file__).resolve().parents[2] / "data" / "raw" / "polymarket" / "events"
OUT_DIR = Path(__file__).resolve().parents[2] / "data" / "raw" / "polymarket" / "price_history"

PRE_WINDOW_DAYS = 35
POST_WINDOW_DAYS = 3
FIDELITY_MINUTES = 60


def _pull_window(scheduled_date, now_ts):
    day = datetime.strptime(scheduled_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    start_ts = int(day.timestamp()) - PRE_WINDOW_DAYS * 86400
    end_ts = int(day.timestamp()) + POST_WINDOW_DAYS * 86400
    return start_ts, min(end_ts, now_ts)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    event_paths = sorted(EVENTS_DIR.glob("*.json"))

    n_attempted = n_no_scheduled_date = n_bad_outcomes = n_skipped_cached = n_written = n_errors = 0
    now_ts = int(time.time())

    for i, path in enumerate(event_paths, start=1):
        event = json.loads(path.read_text())
        parsed = parse_market(event)
        if parsed is None:
            n_no_scheduled_date += 1
            continue

        n_attempted += 1
        event_id = parsed["event_id"]
        out_path = OUT_DIR / f"{event_id}.json"
        if out_path.exists():
            n_skipped_cached += 1
            continue

        market = event["markets"][0]
        if json.loads(market.get("outcomes", "[]")) != ["Yes", "No"]:
            n_bad_outcomes += 1
            continue
        yes_token_id = json.loads(market["clobTokenIds"])[0]

        start_ts, end_ts = _pull_window(parsed["scheduled_date"], now_ts)
        try:
            history = client.get_price_history(yes_token_id, start_ts, end_ts, fidelity=FIDELITY_MINUTES)
        except Exception as e:
            n_errors += 1
            print(f"error on event {event_id} (token {yes_token_id}): {e}")
            continue

        out_path.write_text(json.dumps({
            "event_id": event_id,
            "yes_token_id": yes_token_id,
            "start_ts": start_ts,
            "end_ts": end_ts,
            "history": history,
        }))
        n_written += 1

        if i % 100 == 0:
            print(f"progress: {i}/{len(event_paths)} events scanned, {n_written} written, "
                  f"{n_skipped_cached} skipped (cached), {n_errors} errors")

    print(f"done. events scanned: {len(event_paths)}, no scheduled_date/unparsed: {n_no_scheduled_date}, "
          f"bad outcomes ordering: {n_bad_outcomes}, attempted: {n_attempted}, "
          f"skipped (already cached): {n_skipped_cached}, written: {n_written}, errors: {n_errors}")


if __name__ == "__main__":
    main()
