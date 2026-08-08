import numpy as np
import pandas as pd

from src.strategy.significance import block_bootstrap_sharpe_ci, jobson_korkie_test, permutation_test


def _synthetic_panel(n_dates=12, per_date=4, seed=1):
    """Small non-degenerate panel: n_dates calendar dates, per_date tickers/events each, with a
    direction column that is mostly informative (correlated with the return sign) so net_pnl has
    real variation for both the permutation test and the bootstrap to chew on.
    """
    rng = np.random.default_rng(seed)
    rows = []
    for d in range(n_dates):
        date = pd.Timestamp("2024-01-01") + pd.Timedelta(days=d)
        for j in range(per_date):
            ret = rng.normal(0, 0.05)
            direction = 1 if ret > 0 else -1
            rows.append({
                "event_id": f"{d}-{j}",
                "ticker": f"TICK{j}",
                "scheduled_date": date.strftime("%Y-%m-%d"),
                "direction": direction,
                "return_t_plus_1": ret,
            })
    return pd.DataFrame(rows)


def _price_loader(_ticker):
    """Flat-ish price history so trailing_realized_vol is well-defined and constant for every
    ticker, keeping position sizing simple and non-degenerate for these synthetic tests.
    """
    dates = pd.date_range("2023-10-01", periods=60, freq="D")
    rng = np.random.default_rng(42)
    log_rets = rng.normal(0, 0.01, size=59)
    prices = [100.0]
    for r in log_rets:
        prices.append(prices[-1] * np.exp(r))
    return pd.Series(prices, index=dates)


def test_permutation_test_returns_valid_shape_and_p_value_range():
    df = _synthetic_panel()
    result = permutation_test(
        df, "direction", "t_plus_1", n_permutations=50, seed=0, price_loader=_price_loader,
    )
    assert set(result) == {"observed_sharpe", "null_sharpes", "p_value"}
    assert len(result["null_sharpes"]) == 50
    assert 0.0 <= result["p_value"] <= 1.0
    assert np.isfinite(result["observed_sharpe"])


def test_block_bootstrap_ci_bounds_are_ordered_and_finite():
    df = _synthetic_panel()
    result = block_bootstrap_sharpe_ci(
        df, "direction", "t_plus_1", n_boot=200, seed=0, ci=0.90, price_loader=_price_loader,
    )
    assert set(result) == {"observed_sharpe", "boot_sharpes", "lo", "hi"}
    assert len(result["boot_sharpes"]) == 200
    assert np.isfinite(result["lo"]) and np.isfinite(result["hi"])
    assert result["lo"] <= result["hi"]
    assert np.isfinite(result["observed_sharpe"])


def test_permutation_test_p_value_is_low_when_direction_perfectly_tracks_return_sign():
    # _synthetic_panel constructs direction = sign(return_t_plus_1) exactly, i.e. the best
    # possible sign assignment given this fixed set of trades/magnitudes. Randomly permuting
    # which trades get +1 vs -1 should only rarely do as well, so the one-sided p-value should
    # be low (a sane, non-degenerate check that the test statistic actually discriminates).
    df = _synthetic_panel()
    result = permutation_test(
        df, "direction", "t_plus_1", n_permutations=200, seed=0, price_loader=_price_loader,
    )
    assert result["p_value"] < 0.2


def test_jobson_korkie_identical_series_gives_zero_z_and_p_near_one():
    rng = np.random.default_rng(2)
    dates = pd.date_range("2024-01-01", periods=50, freq="D")
    returns = pd.Series(rng.normal(0.001, 0.02, size=50), index=dates)

    result = jobson_korkie_test(returns, returns.copy())

    assert result["n"] == 50
    assert abs(result["sharpe_a"] - result["sharpe_b"]) < 1e-12
    assert abs(result["z_stat"]) < 1e-9
    assert result["p_value"] > 0.99


def test_jobson_korkie_flags_large_sharpe_gap_between_uncorrelated_series():
    rng = np.random.default_rng(3)
    dates = pd.date_range("2024-01-01", periods=250, freq="D")
    # same volatility, very different mean, independent draws -> large |z|, small p
    high = pd.Series(rng.normal(0.01, 0.01, size=250), index=dates)
    low = pd.Series(rng.normal(0.0, 0.01, size=250), index=dates)

    result = jobson_korkie_test(high, low)

    assert result["sharpe_a"] > result["sharpe_b"]
    assert abs(result["z_stat"]) > 4
    assert result["p_value"] < 0.001


def test_jobson_korkie_aligns_on_shared_index_only():
    dates_a = pd.date_range("2024-01-01", periods=10, freq="D")
    dates_b = pd.date_range("2024-01-05", periods=10, freq="D")
    returns_a = pd.Series(np.linspace(0.01, 0.02, 10), index=dates_a)
    returns_b = pd.Series(np.linspace(-0.01, 0.01, 10), index=dates_b)

    result = jobson_korkie_test(returns_a, returns_b)

    # only the 6 overlapping dates (01-05 through 01-10) should be used
    assert result["n"] == 6
