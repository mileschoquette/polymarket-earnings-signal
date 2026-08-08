import numpy as np
import pandas as pd
import pytest

from src.strategy.backtest import run_backtest, trailing_realized_vol
from src.strategy.signal import compute_signal

WINDOW = 20


def _price_series(start_date, log_returns):
    """n+1 prices starting at start_date (one per calendar day), whose consecutive log returns
    are exactly `log_returns` (length n).
    """
    dates = pd.date_range(start_date, periods=len(log_returns) + 1, freq="D")
    prices = [100.0]
    for r in log_returns:
        prices.append(prices[-1] * np.exp(r))
    return pd.Series(prices, index=dates)


def _alternating_returns(amplitude, n=WINDOW):
    return [amplitude if i % 2 == 0 else -amplitude for i in range(n)]


# 21 prices (2024-01-01 .. 2024-01-21) whose 20 log returns alternate +/-0.01; entry date is the
# very next day so all 21 points are strictly prior to it.
_LOW_VOL_RETURNS = _alternating_returns(0.01)
_LOW_VOL_STD = np.std(_LOW_VOL_RETURNS, ddof=1)
ENTRY_DATE = "2024-01-22"


def _loader(series_by_ticker):
    """Dict-backed price_loader: ticker -> pandas Series of closes indexed by date."""
    return lambda ticker: series_by_ticker[ticker]


def test_deterministic_up_only_case_matches_hand_computed_pnl():
    price_loader = _loader({"AAA": _price_series("2024-01-01", _LOW_VOL_RETURNS)})
    df = pd.DataFrame([{
        "event_id": "1", "ticker": "AAA", "scheduled_date": ENTRY_DATE,
        "direction": 1, "return_t_plus_1": 0.05,
    }])

    result = run_backtest(df, exit_horizon="t_plus_1", cost_bps=5, price_loader=price_loader)
    row = result.iloc[0]

    expected_pos = np.clip(0.02 / _LOW_VOL_STD, 0.1, 3.0)
    expected_gross = 1 * expected_pos * 0.05
    expected_cost = expected_pos * (5 / 10000) * 2
    expected_net = expected_gross - expected_cost

    assert row["position_size"] == pytest.approx(expected_pos)
    assert row["gross_return"] == pytest.approx(expected_gross)
    assert row["cost"] == pytest.approx(expected_cost)
    assert row["net_pnl"] == pytest.approx(expected_net)


def test_flat_signal_gives_zero_pnl_regardless_of_return():
    # price_loader raises if called at all: direction=0 must short-circuit before any vol lookup.
    def _boom(ticker):
        raise AssertionError("vol should never be looked up for a flat (direction=0) event")

    df = pd.DataFrame([{
        "ticker": "AAA", "scheduled_date": ENTRY_DATE, "direction": 0, "return_t_plus_1": 0.9,
    }])
    result = run_backtest(df, price_loader=_boom)
    row = result.iloc[0]

    assert row["position_size"] == 0
    assert row["gross_return"] == 0
    assert row["cost"] == 0
    assert row["net_pnl"] == 0


def test_missing_vol_history_is_treated_as_flat_not_given_a_fallback_size():
    # Only 5 prior points, window=20 requires 21 -> trailing_realized_vol returns None.
    short_history = pd.Series([100.0, 101.0, 99.0, 100.5, 100.2],
                               index=pd.date_range("2024-01-17", periods=5, freq="D"))
    price_loader = _loader({"AAA": short_history})

    df = pd.DataFrame([{
        "ticker": "AAA", "scheduled_date": ENTRY_DATE, "direction": 1, "return_t_plus_1": 0.05,
    }])
    result = run_backtest(df, price_loader=price_loader)
    row = result.iloc[0]

    assert trailing_realized_vol("AAA", ENTRY_DATE, price_loader=price_loader) is None
    assert row["position_size"] == 0
    assert row["gross_return"] == 0
    assert row["net_pnl"] == 0


def test_cost_formula_exact():
    price_loader = _loader({"AAA": _price_series("2024-01-01", _LOW_VOL_RETURNS)})
    df = pd.DataFrame([{
        "ticker": "AAA", "scheduled_date": ENTRY_DATE, "direction": 1, "return_t_plus_1": 0.05,
    }])
    result = run_backtest(df, cost_bps=10, price_loader=price_loader)
    row = result.iloc[0]

    assert row["cost"] == pytest.approx(row["position_size"] * (10 / 10000) * 2)


def test_position_size_is_inversely_proportional_to_trailing_vol():
    lo_returns = _alternating_returns(0.01)
    hi_returns = _alternating_returns(0.02)  # exactly double the amplitude -> exactly double std
    price_loader = _loader({
        "LOWVOL": _price_series("2024-01-01", lo_returns),
        "HIVOL": _price_series("2024-01-01", hi_returns),
    })
    df = pd.DataFrame([
        {"ticker": "LOWVOL", "scheduled_date": ENTRY_DATE, "direction": 1, "return_t_plus_1": 0.05},
        {"ticker": "HIVOL", "scheduled_date": ENTRY_DATE, "direction": 1, "return_t_plus_1": 0.05},
    ])
    result = run_backtest(df, price_loader=price_loader)
    pos_lo = result.loc[result["ticker"] == "LOWVOL", "position_size"].iloc[0]
    pos_hi = result.loc[result["ticker"] == "HIVOL", "position_size"].iloc[0]

    # Neither should be clamped by the leverage bounds, so the ratio should be exactly 2.
    assert 0.1 < pos_lo < 3.0
    assert 0.1 < pos_hi < 3.0
    assert pos_lo / pos_hi == pytest.approx(2.0)


def test_lookahead_trap_future_price_never_affects_trailing_vol():
    base_series = _price_series("2024-01-01", _LOW_VOL_RETURNS)
    vol_before = trailing_realized_vol("AAA", ENTRY_DATE, price_loader=_loader({"AAA": base_series}))

    # Append a wildly different price point strictly AFTER entry_date; a correct implementation
    # must ignore it entirely.
    wild_future = pd.Series(
        [base_series.iloc[-1], 1_000_000.0],
        index=[base_series.index[-1] + pd.Timedelta(days=1), base_series.index[-1] + pd.Timedelta(days=2)],
    )
    contaminated_series = pd.concat([base_series, wild_future.iloc[1:]])
    vol_after = trailing_realized_vol("AAA", ENTRY_DATE, price_loader=_loader({"AAA": contaminated_series}))

    assert vol_before == pytest.approx(_LOW_VOL_STD)
    assert vol_after == pytest.approx(vol_before)


def test_signal_no_lookahead_later_event_never_changes_earlier_direction():
    def _make_df(later_divergence):
        rows = [
            {"event_id": "A", "ticker": "T", "scheduled_date": "2024-01-01", "implied_prob_pre_earnings": 1.0, "historical_beat_rate": 0.0},
            {"event_id": "B", "ticker": "T", "scheduled_date": "2024-01-01", "implied_prob_pre_earnings": -1.0, "historical_beat_rate": 0.0},
            {"event_id": "C", "ticker": "T", "scheduled_date": "2024-01-02", "implied_prob_pre_earnings": 5.0, "historical_beat_rate": 0.0},
            {"event_id": "D", "ticker": "T", "scheduled_date": "2024-01-03", "implied_prob_pre_earnings": 4.0, "historical_beat_rate": 0.0},
            {"event_id": "E", "ticker": "T", "scheduled_date": "2024-01-03", "implied_prob_pre_earnings": -3.0, "historical_beat_rate": 0.0},
            {"event_id": "F", "ticker": "T", "scheduled_date": "2024-01-04", "implied_prob_pre_earnings": later_divergence, "historical_beat_rate": 0.0},
        ]
        return pd.DataFrame(rows)

    result_1 = compute_signal(_make_df(0.0), threshold_sd=1.0, min_history=2)
    result_2 = compute_signal(_make_df(999.0), threshold_sd=1.0, min_history=2)

    earlier_ids = ["A", "B", "C", "D", "E"]
    dir_1 = result_1.set_index("event_id").loc[earlier_ids, "direction"]
    dir_2 = result_2.set_index("event_id").loc[earlier_ids, "direction"]
    pd.testing.assert_series_equal(dir_1, dir_2)

    # Hand-computed expected directions under the correct (strictly-prior, no-lookahead) rule:
    by_id = result_1.set_index("event_id")
    # day 1: 0 prior observations (< min_history=2) -> flat regardless of magnitude.
    assert by_id.loc["A", "direction"] == 0
    assert by_id.loc["B", "direction"] == 0
    # day 2: prior = [1.0, -1.0] (from day 1) -> threshold = std([1,-1], ddof=1) = sqrt(2).
    assert by_id.loc["C", "direction"] == 1  # 5.0 > sqrt(2)
    # day 3: prior = [1.0, -1.0, 5.0] -> threshold = std(..., ddof=1) ~= 3.055.
    assert by_id.loc["D", "direction"] == 1  # 4.0 > 3.055
    # E must NOT see D's divergence (same-day leak) even though D is processed first in the
    # dataframe: with D's 4.0 leaked into the prior set the threshold drops to ~2.754 and -3.0
    # would (wrongly) cross it; using only the correct day-1/day-2 prior, -3.0 stays inside the
    # +/-3.055 band -> flat.
    assert by_id.loc["E", "direction"] == 0


def test_signal_null_divergence_is_left_flat():
    df = pd.DataFrame([
        {"event_id": "A", "ticker": "T", "scheduled_date": "2024-01-01", "implied_prob_pre_earnings": None, "historical_beat_rate": 0.0},
    ])
    result = compute_signal(df, threshold_sd=0.5, min_history=0)
    assert result.loc[0, "direction"] == 0


def test_aggregate_by_date_sums_same_day_events():
    from src.strategy.performance import aggregate_by_date

    pnl = pd.Series([1.0, 2.0, 3.0])
    dates = ["2024-01-01", "2024-01-01", "2024-01-02"]
    result = aggregate_by_date(pnl, dates)
    assert result.loc[pd.Timestamp("2024-01-01")] == 3.0
    assert result.loc[pd.Timestamp("2024-01-02")] == 3.0
    assert len(result) == 2


def test_dates_per_year_counts_distinct_dates_not_events():
    from src.strategy.performance import dates_per_year

    # 3 events on 2 distinct dates, ~1 year apart -> ~2 distinct dates / 1 year (loose tolerance:
    # 2024 is a leap year, so 366 actual days vs the 365.25-day average year used for annualizing)
    dates = ["2024-01-01", "2024-01-01", "2025-01-01"]
    result = dates_per_year(dates)
    assert abs(result - 2.0) < 0.01


def test_max_drawdown_hand_computable():
    from src.strategy.performance import max_drawdown

    # cumsum: 0.5, -0.3, -1.1, -0.6 -> running peak 0.5 throughout -> trough (cum - peak) = -1.6
    pnl = pd.Series([0.5, -0.8, -0.8, 0.5])
    assert abs(max_drawdown(pnl) - (-1.6)) < 1e-12


def test_max_drawdown_is_not_bounded_at_minus_one():
    from src.strategy.performance import max_drawdown

    # This project's max_drawdown sums risk-scaled per-event/per-date returns rather than
    # compounding them into a bounded NAV ratio (see the function's own docstring), so a run of
    # leveraged losing periods can push cumulative summed P&L below -1. A drawdown below -1 is
    # therefore not, by itself, evidence of a bug -- this test pins that down so a future reader
    # doesn't "fix" it into the bounded [-1, 0] convention used by percentage-of-peak drawdown.
    pnl = pd.Series([0.1, -0.9, -0.9])
    assert max_drawdown(pnl) < -1.0
