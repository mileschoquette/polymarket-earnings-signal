import numpy as np
import pandas as pd

from src.strategy.benchmarks import (
    buy_and_hold_direction,
    historical_only_direction,
    perfect_foresight_direction,
    permuted_direction,
)


def test_buy_and_hold_is_always_long_regardless_of_input():
    df = pd.DataFrame({
        "ticker": ["A", "B", "C"],
        "scheduled_date": ["2024-01-01", "2024-01-02", "2024-01-03"],
        "implied_prob_pre_earnings": [0.9, 0.1, np.nan],
        "historical_beat_rate": [0.1, 0.9, 0.5],
    })
    result = buy_and_hold_direction(df)
    assert (result["direction"] == 1).all()
    assert len(result) == len(df)


def test_historical_only_no_lookahead_later_event_never_changes_earlier_direction():
    # Mirrors test_signal_no_lookahead_later_event_never_changes_earlier_direction in
    # tests/test_backtest_pnl.py, adapted to threshold historical_beat_rate - 0.5 instead of
    # implied_prob_pre_earnings - historical_beat_rate.
    def _make_df(later_beat_rate):
        rows = [
            {"event_id": "A", "ticker": "T", "scheduled_date": "2024-01-01", "historical_beat_rate": 1.0 + 0.5},
            {"event_id": "B", "ticker": "T", "scheduled_date": "2024-01-01", "historical_beat_rate": -1.0 + 0.5},
            {"event_id": "C", "ticker": "T", "scheduled_date": "2024-01-02", "historical_beat_rate": 5.0 + 0.5},
            {"event_id": "D", "ticker": "T", "scheduled_date": "2024-01-03", "historical_beat_rate": 4.0 + 0.5},
            {"event_id": "E", "ticker": "T", "scheduled_date": "2024-01-03", "historical_beat_rate": -3.0 + 0.5},
            {"event_id": "F", "ticker": "T", "scheduled_date": "2024-01-04", "historical_beat_rate": later_beat_rate},
        ]
        return pd.DataFrame(rows)

    result_1 = historical_only_direction(_make_df(0.5), threshold_sd=1.0, min_history=2)
    result_2 = historical_only_direction(_make_df(999.0), threshold_sd=1.0, min_history=2)

    earlier_ids = ["A", "B", "C", "D", "E"]
    dir_1 = result_1.set_index("event_id").loc[earlier_ids, "direction"]
    dir_2 = result_2.set_index("event_id").loc[earlier_ids, "direction"]
    pd.testing.assert_series_equal(dir_1, dir_2)

    by_id = result_1.set_index("event_id")
    assert by_id.loc["A", "direction"] == 0
    assert by_id.loc["B", "direction"] == 0
    assert by_id.loc["C", "direction"] == 1
    assert by_id.loc["D", "direction"] == 1
    assert by_id.loc["E", "direction"] == 0


def test_perfect_foresight_matches_two_times_actual_beat_minus_one():
    df = pd.DataFrame({
        "ticker": ["A", "B", "C", "D"],
        "scheduled_date": ["2024-01-01"] * 4,
        "actual_beat": [1, 0, 1, 0],
    })
    result = perfect_foresight_direction(df)
    assert list(result["direction"]) == [1, -1, 1, -1]


def test_permuted_direction_preserves_flat_mask_and_pos_neg_counts_but_reassigns_signs():
    df = pd.DataFrame({"direction": [1, -1, 0, 1, -1, 1, 0, -1]})
    rng = np.random.default_rng(0)
    permuted = permuted_direction(df, "direction", rng)

    original = df["direction"]
    assert (permuted[original == 0] == 0).all()
    assert (permuted[original != 0] != 0).all()
    assert (permuted != 0).sum() == (original != 0).sum()
    assert (permuted == 1).sum() == (original == 1).sum()
    assert (permuted == -1).sum() == (original == -1).sum()

    # With this seed the assignment should actually move at least one sign around (not a no-op).
    assert not permuted.equals(original)
