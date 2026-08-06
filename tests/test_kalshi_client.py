from unittest.mock import Mock, patch

import pytest

from src.kalshi_client import client


@pytest.fixture(autouse=True)
def _no_throttle(monkeypatch):
    monkeypatch.setattr(client, "MIN_REQUEST_INTERVAL", 0.0)
    monkeypatch.setattr(client.time, "sleep", lambda _: None)


def _mock_response(status_code=200, json_data=None):
    resp = Mock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.raise_for_status = Mock()
    return resp


def test_list_events_paginates_via_cursor():
    page1 = _mock_response(json_data={"events": [{"event_ticker": "FED-21JUL"}], "cursor": "abc"})
    page2 = _mock_response(json_data={"events": [{"event_ticker": "KXFED-26APR"}], "cursor": ""})
    with patch.object(client.requests, "get", side_effect=[page1, page2]):
        events = client.list_events("KXFED")
    assert [e["event_ticker"] for e in events] == ["FED-21JUL", "KXFED-26APR"]


def test_get_market_falls_back_to_historical_on_404():
    live_404 = _mock_response(status_code=404)
    live_404.raise_for_status.side_effect = client.requests.HTTPError
    historical_200 = _mock_response(json_data={"market": {"ticker": "FED-23FEB-T4.50"}})
    with patch.object(client.requests, "get", side_effect=[live_404, historical_200]):
        market = client.get_market("FED-23FEB-T4.50")
    assert market["market"]["ticker"] == "FED-23FEB-T4.50"


def test_get_falls_back_to_mirror_host_on_non_200():
    primary_fail = _mock_response(status_code=500)
    mirror_ok = _mock_response(json_data={"events": [], "cursor": ""})
    with patch.object(client.requests, "get", side_effect=[primary_fail, mirror_ok]) as mock_get:
        client.list_events("KXFED")
    called_urls = [call.args[0] for call in mock_get.call_args_list]
    assert called_urls[0].startswith(client.BASE_URL)
    assert called_urls[1].startswith(client.FALLBACK_BASE_URL)


def test_backoff_retries_on_429_then_succeeds():
    rate_limited = _mock_response(status_code=429)
    ok = _mock_response(json_data={"events": [], "cursor": ""})
    with patch.object(client.requests, "get", side_effect=[rate_limited, ok]):
        client.list_events("KXFED")


def test_list_markets_for_event_falls_back_to_historical_when_empty():
    live_empty = _mock_response(json_data={"markets": [], "cursor": ""})
    historical_full = _mock_response(json_data={"markets": [{"ticker": "FED-23FEB-T4.50"}], "cursor": ""})
    with patch.object(client.requests, "get", side_effect=[live_empty, historical_full]):
        markets = client.list_markets_for_event("FED-23FEB")
    assert markets[0]["ticker"] == "FED-23FEB-T4.50"
