from unittest.mock import Mock, patch

import pytest

from src.polymarket_client import client


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


def test_list_events_paginates_via_cursor_until_next_cursor_is_none():
    page1 = _mock_response(json_data={"events": [{"id": "1"}], "next_cursor": "abc"})
    page2 = _mock_response(json_data={"events": [{"id": "2"}], "next_cursor": None})
    with patch.object(client.requests, "get", side_effect=[page1, page2]):
        events = client.list_events(tag_id=1013)
    assert [e["id"] for e in events] == ["1", "2"]


def test_list_events_stops_on_empty_page():
    page1 = _mock_response(json_data={"events": [{"id": "1"}], "next_cursor": "abc"})
    page2 = _mock_response(json_data={"events": [], "next_cursor": "abc"})
    with patch.object(client.requests, "get", side_effect=[page1, page2]):
        events = client.list_events(tag_id=1013)
    assert [e["id"] for e in events] == ["1"]


def test_get_price_history_chunks_wide_ranges():
    start_ts = 0
    end_ts = client.PRICE_HISTORY_CHUNK_SECONDS * 3  # spans 3 chunks
    chunk1 = _mock_response(json_data={"history": [{"t": 1, "p": 0.5}]})
    chunk2 = _mock_response(json_data={"history": [{"t": 2, "p": 0.6}]})
    chunk3 = _mock_response(json_data={"history": [{"t": 3, "p": 0.7}]})
    with patch.object(client.requests, "get", side_effect=[chunk1, chunk2, chunk3]) as mock_get:
        points = client.get_price_history("token123", start_ts, end_ts)
    assert len(points) == 3
    assert mock_get.call_count == 3
    first_call_params = mock_get.call_args_list[0].kwargs["params"]
    assert first_call_params["endTs"] - first_call_params["startTs"] == client.PRICE_HISTORY_CHUNK_SECONDS


def test_get_price_history_single_chunk_for_narrow_range():
    chunk = _mock_response(json_data={"history": [{"t": 1, "p": 0.5}]})
    with patch.object(client.requests, "get", side_effect=[chunk]) as mock_get:
        points = client.get_price_history("token123", 0, 86400)
    assert len(points) == 1
    assert mock_get.call_count == 1


def test_backoff_retries_on_429_then_succeeds():
    rate_limited = _mock_response(status_code=429)
    ok = _mock_response(json_data={"events": [], "next_cursor": None})
    with patch.object(client.requests, "get", side_effect=[rate_limited, ok]):
        client.list_events(tag_id=1013)
