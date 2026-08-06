import numpy as np
import pandas as pd
import pytest

from src.analysis import event_reaction as er

DATES = ["2025-06-01", "2025-06-02", "2025-06-03", "2025-06-04", "2025-06-05", "2025-06-06"]
SCHEDULED_DATE = "2025-06-07"  # T-5d = 2025-06-02, T-1d = 2025-06-06 given MOMENTUM_DAYS = [5, 1]


def _closes(prices):
    idx = pd.DatetimeIndex(pd.to_datetime(DATES)).tz_localize("America/New_York")
    return pd.Series(prices, index=idx)


@pytest.fixture(autouse=True)
def _clear_cache():
    er._price_cache.clear()
    yield
    er._price_cache.clear()


def test_car_pre_is_zero_when_stock_and_market_are_both_flat():
    er._price_cache["FLAT"] = _closes([100.0] * 6)
    er._price_cache["SPY"] = _closes([500.0] * 6)
    assert er.car_pre("FLAT", SCHEDULED_DATE) == pytest.approx(0.0)


def test_car_pre_matches_hand_computed_value():
    # stock: 100 -> 110 on the T-5d/T-1d target dates (10% return)
    # SPY:    500 -> 510 on the same dates (2% return)
    # car_pre = 0.10 - 0.02 = 0.08
    er._price_cache["KNOWN"] = _closes([98, 100, 101, 103, 107, 110])
    er._price_cache["SPY"] = _closes([495, 500, 502, 505, 508, 510])
    assert er.car_pre("KNOWN", SCHEDULED_DATE) == pytest.approx(0.08)


def test_build_car_pre_skips_rows_with_missing_ticker_data():
    er._price_cache["KNOWN"] = _closes([98, 100, 101, 103, 107, 110])
    er._price_cache["SPY"] = _closes([495, 500, 502, 505, 508, 510])
    df = pd.DataFrame({
        "ticker": ["KNOWN", "MISSING_TICKER_ZZZ"],
        "scheduled_date": [SCHEDULED_DATE, SCHEDULED_DATE],
    })
    out = er.build_car_pre(df)
    assert out.loc[0, "car_pre"] == pytest.approx(0.08)
    assert pd.isna(out.loc[1, "car_pre"])


def test_regression_recovers_planted_momentum_coefficient():
    # car_pre = alpha + beta*momentum + noise, with a known planted beta; tolerance is 3 cluster-
    # robust SEs, the standard "does the CI cover the truth" bar for a single well-powered draw.
    rng = np.random.default_rng(0)
    n = 2000
    alpha_true, beta_true = 0.01, 0.5
    momentum = rng.normal(0, 0.1, n)
    noise = rng.normal(0, 0.05, n)
    car = alpha_true + beta_true * momentum + noise
    df = pd.DataFrame({
        "car_pre": car,
        "implied_prob_momentum": momentum,
        "scheduled_date": rng.integers(0, n // 5, n).astype(str),
    })
    result = er.fit_car_regression(df)
    coef = result.params["implied_prob_momentum"]
    se = result.bse["implied_prob_momentum"]
    assert abs(coef - beta_true) < 3 * se
