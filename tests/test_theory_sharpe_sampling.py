import numpy as np

from src.theory.sharpe_sampling import lo_2002_se, simulate_null_sharpe_distribution


def test_lo_se_annualization_consistency():
    # SE_annual(S, N, q) must equal sqrt(q) * per_period_formula(S/sqrt(q), N) by construction --
    # this is the identity that guards against the units bug (using S directly in the per-period
    # formula without converting first, which would understate the SE by roughly sqrt(q)).
    sharpe_annual, n_periods, q = 1.095, 181, 150.0
    se = lo_2002_se(sharpe_annual, n_periods, q)

    sharpe_period = sharpe_annual / np.sqrt(q)
    per_period_se = np.sqrt((1 + 0.5 * sharpe_period**2) / n_periods)
    expected = np.sqrt(q) * per_period_se
    assert abs(se - expected) < 1e-12

    # the naive (buggy) version -- plugging sharpe_annual directly into the per-period formula --
    # must NOT match; it understates the SE by roughly sqrt(q).
    buggy = np.sqrt((1 + 0.5 * sharpe_annual**2) / n_periods)
    assert se > 5 * buggy


def test_lo_se_matches_paper_order_of_magnitude():
    # ~181 independent trading dates over ~14.5 months of coverage -> periods_per_year ~150.
    se = lo_2002_se(sharpe_annual=1.095, n_periods=181, periods_per_year=181 / (14.5 / 12))
    assert 0.7 < se < 1.1


def test_null_sharpe_distribution_centered_near_zero_and_matches_lo_se_order_of_magnitude():
    daily_pnl_std, n_dates, q = 0.02, 181, 150.0
    sim = simulate_null_sharpe_distribution(daily_pnl_std, n_dates, q, n_sim=4000, seed=0)

    assert abs(sim.mean()) < 0.15
    lo_se = lo_2002_se(sharpe_annual=0.0, n_periods=n_dates, periods_per_year=q)
    empirical_se = sim.std(ddof=1)
    assert lo_se / 2 < empirical_se < lo_se * 2


def test_simulate_null_sharpe_distribution_is_deterministic_given_seed():
    sim_a = simulate_null_sharpe_distribution(0.02, 181, 150.0, n_sim=100, seed=7)
    sim_b = simulate_null_sharpe_distribution(0.02, 181, 150.0, n_sim=100, seed=7)
    assert np.array_equal(sim_a, sim_b)
