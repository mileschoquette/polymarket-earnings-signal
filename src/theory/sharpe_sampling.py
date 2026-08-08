"""Bridges the paper's empirical Sharpe-ratio significance tests to Lo (2002, "The Statistics of
Sharpe Ratios," Financial Analysts Journal, 58(4), 36-52)'s asymptotic standard error, and to a
Monte Carlo null-hypothesis sampling distribution built from this paper's own data structure.

Lo's delta-method result is stated PER PERIOD: for i.i.d. per-period returns with per-period Sharpe
SR_t observed over N periods, SE(SR_t_hat) = sqrt((1 + 0.5*SR_t**2) / N). Plugging an ANNUALIZED
Sharpe directly into that formula (skipping the per-period conversion) understates the SE by
roughly sqrt(periods_per_year), since it silently treats each of the N periods as spanning a full
year of variance rather than 1/periods_per_year of one. `lo_2002_se` converts to per-period terms
first and annualizes the resulting SE back up, which is the only unit-consistent way to compare
Lo's formula against an annualized Sharpe estimate.
"""
import numpy as np
import pandas as pd

from src.strategy.performance import annualized_sharpe


def lo_2002_se(sharpe_annual, n_periods, periods_per_year):
    """Properly-annualized Lo (2002) standard error for an annualized Sharpe ratio estimated over
    n_periods independent periods (e.g. distinct trading dates), sampled periods_per_year times a
    year. Converts to Lo's native per-period units (sharpe_period = sharpe_annual / sqrt(q)),
    applies SE_period = sqrt((1 + 0.5*sharpe_period**2) / n_periods), then annualizes the SE back
    up by sqrt(q) -- the same sqrt(q) factor that separates an annualized Sharpe from its per-period
    counterpart. Skipping this conversion (using sharpe_annual directly in Lo's per-period formula)
    understates the SE by roughly sqrt(periods_per_year).
    """
    q = periods_per_year
    sharpe_period = sharpe_annual / np.sqrt(q)
    se_period = np.sqrt((1 + 0.5 * sharpe_period**2) / n_periods)
    return np.sqrt(q) * se_period


def simulate_null_sharpe_distribution(daily_pnl_std, n_dates, periods_per_year, n_sim=1000, seed=0):
    """Monte Carlo sampling distribution of the annualized Sharpe ratio under H0: true per-date
    P&L mean is 0, calibrated to the observed daily_pnl_std and n_dates. Each simulation draws
    n_dates i.i.d. N(0, daily_pnl_std**2) values and computes the annualized Sharpe via
    `annualized_sharpe` (src/strategy/performance.py), the same formula convention used everywhere
    else in this project, rather than a separately-defined one here. Returns an array of n_sim
    simulated Sharpe ratios.
    """
    rng = np.random.default_rng(seed)
    draws = rng.normal(0, daily_pnl_std, size=(n_sim, n_dates))
    return np.array([annualized_sharpe(pd.Series(row), periods_per_year) for row in draws])
