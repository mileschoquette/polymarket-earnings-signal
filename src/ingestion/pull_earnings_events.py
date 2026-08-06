"""Pull Polymarket earnings-tag events (closed and open) and cache them as raw JSON."""
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from src.polymarket_client import client

EVENTS_DIR = Path(__file__).resolve().parents[2] / "data" / "raw" / "polymarket" / "events"
MANIFEST_PATH = Path(__file__).resolve().parents[2] / "data" / "raw" / "_manifest.csv"
MANIFEST_HEADER = ["event_id", "closed", "pulled_at_iso", "slug"]


def _append_manifest_row(event_id, closed, slug):
    is_new = not MANIFEST_PATH.exists()
    with MANIFEST_PATH.open("a", newline="") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(MANIFEST_HEADER)
        writer.writerow([event_id, closed, datetime.now(timezone.utc).isoformat(), slug])


def _write_event(event, closed):
    """Cache one event as JSON. Closed events are immutable and never rewritten;
    open events are still live/updating so they're always overwritten with the latest pull."""
    event_id = event["id"]
    path = EVENTS_DIR / f"{event_id}.json"
    if closed and path.exists():
        return False
    path.write_text(json.dumps(event, indent=2))
    _append_manifest_row(event_id, closed, event.get("slug"))
    return True


def pull_events(closed):
    events = client.list_events(closed=closed)
    written = sum(_write_event(event, closed) for event in events)
    return len(events), written


def main():
    EVENTS_DIR.mkdir(parents=True, exist_ok=True)

    n_closed, w_closed = pull_events(closed=True)
    print(f"closed events: fetched {n_closed}, written {w_closed} (skipped {n_closed - w_closed} already cached)")

    n_open, w_open = pull_events(closed=False)
    print(f"open events: fetched {n_open}, written {w_open} (always overwritten)")

    print(f"total files in {EVENTS_DIR}: {len(list(EVENTS_DIR.glob('*.json')))}")


if __name__ == "__main__":
    main()
