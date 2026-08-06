import time
from pathlib import Path

import requests
import yaml

from .rate_limit import request_with_backoff

_config_path = Path(__file__).resolve().parents[2] / "config" / "series_config.yaml"
_config = yaml.safe_load(_config_path.read_text())["kalshi_api"]

BASE_URL = _config["base_url"]
FALLBACK_BASE_URL = _config["fallback_base_url"]
MIN_REQUEST_INTERVAL = 0.34  # ~3 req/sec; unauthenticated rate limits aren't published, so be conservative

_last_request_time = [0.0]


def _throttle():
    elapsed = time.time() - _last_request_time[0]
    if elapsed < MIN_REQUEST_INTERVAL:
        time.sleep(MIN_REQUEST_INTERVAL - elapsed)
    _last_request_time[0] = time.time()


def _get(path, params=None, base_url=None):
    """GET a Kalshi market-data endpoint, falling back to the mirror host on a non-200."""
    base_url = base_url or BASE_URL
    _throttle()
    resp = request_with_backoff(lambda: requests.get(f"{base_url}{path}", params=params, timeout=10))
    if resp.status_code != 200 and base_url == BASE_URL:
        return _get(path, params=params, base_url=FALLBACK_BASE_URL)
    resp.raise_for_status()
    return resp.json()


def get_historical_cutoff():
    return _get("/historical/cutoff")


def list_events(series_ticker, status=None):
    """Enumerate all events for a series. Not affected by the live/historical split, so this sees full history even across ticker renames."""
    events = []
    cursor = None
    while True:
        params = {"series_ticker": series_ticker, "limit": 200}
        if status:
            params["status"] = status
        if cursor:
            params["cursor"] = cursor
        data = _get("/events", params=params)
        events.extend(data.get("events", []))
        cursor = data.get("cursor")
        if not cursor:
            break
    return events


def get_event(event_ticker):
    return _get(f"/events/{event_ticker}")


def list_markets_for_event(event_ticker, historical=False):
    """List all markets under one event, trying the live endpoint first and falling back to /historical/* if empty."""
    path = "/historical/markets" if historical else "/markets"
    markets = []
    cursor = None
    while True:
        params = {"event_ticker": event_ticker, "limit": 200}
        if cursor:
            params["cursor"] = cursor
        data = _get(path, params=params)
        markets.extend(data.get("markets", []))
        cursor = data.get("cursor")
        if not cursor:
            break
    if not markets and not historical:
        return list_markets_for_event(event_ticker, historical=True)
    return markets


def get_market(ticker, historical=False):
    """Fetch one market, falling back to the historical endpoint if the live one 404s."""
    path = f"/historical/markets/{ticker}" if historical else f"/markets/{ticker}"
    try:
        return _get(path)
    except requests.HTTPError:
        if not historical:
            return get_market(ticker, historical=True)
        raise


def get_orderbook(ticker, depth=0):
    return _get(f"/markets/{ticker}/orderbook", params={"depth": depth})


def get_candlesticks(series_ticker, ticker, start_ts, end_ts, period_interval=1440, historical=False):
    """Candlesticks for one market. period_interval is in minutes: 1, 60, or 1440 only. start_ts/end_ts are unix seconds."""
    path = (
        f"/historical/markets/{ticker}/candlesticks"
        if historical
        else f"/series/{series_ticker}/markets/{ticker}/candlesticks"
    )
    params = {"start_ts": start_ts, "end_ts": end_ts, "period_interval": period_interval}
    data = _get(path, params=params)
    if not data.get("candlesticks") and not historical:
        return get_candlesticks(series_ticker, ticker, start_ts, end_ts, period_interval, historical=True)
    return data
