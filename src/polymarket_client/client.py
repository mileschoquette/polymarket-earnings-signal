import time
from pathlib import Path

import requests
import yaml

from .rate_limit import request_with_backoff

_config_path = Path(__file__).resolve().parents[2] / "config" / "earnings_config.yaml"
_config = yaml.safe_load(_config_path.read_text())

GAMMA_BASE_URL = _config["polymarket_api"]["gamma_base_url"]
CLOB_BASE_URL = _config["polymarket_api"]["clob_base_url"]
EARNINGS_TAG_ID = _config["polymarket_api"]["earnings_tag_id"]
EVENTS_PAGE_SIZE = _config["ingestion"]["events_page_size"]

MIN_REQUEST_INTERVAL = 0.1  # no documented or observed rate limit, but stay polite
PRICE_HISTORY_CHUNK_SECONDS = 14 * 86400  # API caps startTs/endTs interval at ~15-16 days regardless of fidelity

_last_request_time = [0.0]


def _throttle():
    elapsed = time.time() - _last_request_time[0]
    if elapsed < MIN_REQUEST_INTERVAL:
        time.sleep(MIN_REQUEST_INTERVAL - elapsed)
    _last_request_time[0] = time.time()


def _get(base_url, path, params=None):
    _throttle()
    resp = request_with_backoff(lambda: requests.get(f"{base_url}{path}", params=params, timeout=10))
    resp.raise_for_status()
    return resp.json()


def list_events(tag_id=None, closed=True):
    """Enumerate all events for a tag via cursor-based keyset pagination (offset pagination 422s past offset=2000)."""
    tag_id = tag_id or EARNINGS_TAG_ID
    events = []
    cursor = None
    while True:
        params = {"tag_id": tag_id, "closed": str(closed).lower(), "limit": EVENTS_PAGE_SIZE}
        if cursor:
            params["after_cursor"] = cursor
        data = _get(GAMMA_BASE_URL, "/events/keyset", params=params)
        page = data.get("events", [])
        events.extend(page)
        cursor = data.get("next_cursor")
        if not page or cursor is None:
            break
    return events


def get_price_history(token_id, start_ts, end_ts, fidelity=60):
    """Implied-probability history for one CLOB token, chunked into <=14-day windows (API rejects wider intervals at any fidelity)."""
    points = []
    chunk_start = start_ts
    while chunk_start < end_ts:
        chunk_end = min(chunk_start + PRICE_HISTORY_CHUNK_SECONDS, end_ts)
        data = _get(
            CLOB_BASE_URL,
            "/prices-history",
            params={"market": token_id, "startTs": chunk_start, "endTs": chunk_end, "fidelity": fidelity},
        )
        points.extend(data.get("history", []))
        chunk_start = chunk_end
    return points
