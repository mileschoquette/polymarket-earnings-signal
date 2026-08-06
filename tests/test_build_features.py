import copy

from src.processing.build_features import build_features, shrunk_beat_rate


def _event(event_id, ticker, scheduled_date, consensus_eps, closed_yes):
    """closed_yes: True -> resolved Yes (beat), False -> resolved No (miss), None -> still open."""
    if closed_yes is None:
        market = {"closed": False, "outcomePrices": None}
    else:
        market = {"closed": True, "outcomePrices": json_dumps(["1", "0"] if closed_yes else ["0", "1"])}
    return {
        "id": event_id,
        "title": f"Will Example ({ticker}) beat quarterly earnings?",
        "markets": [
            {
                **market,
                "slug": f"{ticker.lower()}-quarterly-earnings-nongaap-eps-{scheduled_date.replace('-', '-')}-x",
                "description": (
                    f"As of market creation, Example is estimated to release earnings on "
                    f"{_month_name(scheduled_date)}. The Street consensus estimate for Example's "
                    f"non-GAAP EPS for the relevant quarter is ${consensus_eps} as of market creation."
                ),
            }
        ],
    }


def json_dumps(x):
    import json

    return json.dumps(x)


def _month_name(iso_date):
    from datetime import datetime

    d = datetime.strptime(iso_date, "%Y-%m-%d")
    return d.strftime("%B %d, %Y")


def _price_history(points):
    return {"history": [{"t": t, "p": p} for t, p in points]}


def test_shrunk_beat_rate_with_no_prior_history_returns_global_rate():
    assert shrunk_beat_rate([], [1, 1, 0, 1]) == 0.75


def test_shrunk_beat_rate_with_no_history_at_all_returns_half():
    assert shrunk_beat_rate([], []) == 0.5


def test_shrunk_beat_rate_blends_ticker_and_global():
    # 4 prior ticker beats (all 1s), global rate 0.5, prior_strength=4 -> (4*1 + 4*0.5) / 8 = 0.75
    result = shrunk_beat_rate([1, 1, 1, 1], [1, 0, 1, 0, 1, 0])
    assert abs(result - 0.75) < 1e-9


def test_no_lookahead_ticker_baseline_excludes_current_and_future_events():
    events = {
        "1": _event("1", "AAA", "2024-01-01", "1.00", closed_yes=True),
        "2": _event("2", "AAA", "2024-04-01", "1.00", closed_yes=False),
        "3": _event("3", "AAA", "2024-07-01", "1.00", closed_yes=True),
    }
    price_histories = {}
    features = build_features(events, price_histories)

    # event 1: no prior AAA history -> falls back to global rate (no prior global events either -> 0.5)
    assert features["1"]["historical_beat_rate"] == 0.5
    # event 2: only event 1's outcome (beat=1) is prior; must not see event 2's own outcome or event 3's
    assert features["2"]["historical_beat_rate"] == shrunk_beat_rate([1], [1])
    # event 3: events 1 and 2 are prior (beat=1, beat=0); must not see its own outcome
    assert features["3"]["historical_beat_rate"] == shrunk_beat_rate([1, 0], [1, 0])


def test_no_lookahead_same_day_events_do_not_leak_into_each_other():
    events = {
        "1": _event("1", "AAA", "2024-01-01", "1.00", closed_yes=True),
        "2": _event("2", "BBB", "2024-01-01", "1.00", closed_yes=False),
    }
    features = build_features(events, {})
    # both report on the same day with no prior history at all -> both see an empty global backstop
    assert features["1"]["historical_beat_rate"] == 0.5
    assert features["2"]["historical_beat_rate"] == 0.5


def test_skips_events_without_resolved_outcome():
    events = {"1": _event("1", "AAA", "2024-01-01", "1.00", closed_yes=None)}
    features = build_features(events, {})
    assert features == {}


def test_snapshot_and_momentum_use_most_recent_point_at_or_before_target():
    from src.processing.build_features import _snapshot_ts

    scheduled_date = "2024-01-10"
    far_ts = _snapshot_ts(scheduled_date, 5)  # 2024-01-05
    near_ts = _snapshot_ts(scheduled_date, 1)  # 2024-01-09

    price_history = _price_history(
        [
            (far_ts - 3600, 0.40),  # at/before far snapshot
            (far_ts + 1800, 0.55),  # after far snapshot, before near snapshot -> should NOT be picked for "far"
            (near_ts - 3600, 0.70),  # at/before near snapshot
            (near_ts + 7200, 0.99),  # after near snapshot -> must never be used (look-ahead trap)
        ]
    )
    events = {"1": _event("1", "AAA", scheduled_date, "1.00", closed_yes=True)}
    features = build_features(events, {"1": price_history})

    assert features["1"]["implied_prob_pre_earnings"] == 0.70
    assert abs(features["1"]["implied_prob_momentum"] - (0.70 - 0.40)) < 1e-9


def test_missing_price_history_gives_none_snapshot_and_momentum():
    events = {"1": _event("1", "AAA", "2024-01-10", "1.00", closed_yes=True)}
    features = build_features(events, {})
    assert features["1"]["implied_prob_pre_earnings"] is None
    assert features["1"]["implied_prob_momentum"] is None


def test_history_window_caps_ticker_lookback():
    # 9 prior beats (all 1s) but window is 8 -> only the most recent 8 should count
    events = {}
    for i in range(9):
        events[str(i)] = _event(str(i), "AAA", f"2020-{(i % 12) + 1:02d}-01", "1.00", closed_yes=True)
    events["9"] = _event("9", "AAA", "2021-01-01", "1.00", closed_yes=False)

    features = build_features(copy.deepcopy(events), {})
    # all 9 prior events beat (1), window=8 caps at 8 observations, all still 1s -> same as using all 9
    assert features["9"]["historical_beat_rate"] == shrunk_beat_rate([1] * 8, [1] * 9)
