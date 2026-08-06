"""Significance checks for the divergence-signal backtest: does the observed date-aggregated
Sharpe beat what random direction assignment (same trade selection, timing, and sizing) would
produce, and how wide is the sampling uncertainty once same-day event clustering is respected?
"""
import numpy as np
import pandas as pd

from src.strategy.backtest import run_backtest
from src.strategy.benchmarks import permuted_direction
from src.strategy.performance import aggregate_by_date, annualized_sharpe, dates_per_year


def _date_aggregated_sharpe(result):
    """Annualized Sharpe on the date-aggregated net_pnl of a run_backtest result (same-day
    events summed into one observation per calendar date, the more defensible number here).
    """
    daily_pnl = aggregate_by_date(result["net_pnl"], result["scheduled_date"])
    return annualized_sharpe(daily_pnl, dates_per_year(result["scheduled_date"]))


def permutation_test(df, main_direction_col, exit_horizon, n_permutations=1000, seed=0, **backtest_kwargs):
    """Observed date-aggregated Sharpe from df[main_direction_col] vs n_permutations null Sharpes
    from permuted_direction draws of that same column (identical trade selection/timing/sizing,
    only the sign scrambled among the events that traded). Returns {observed_sharpe, null_sharpes,
    p_value}, where p_value is the fraction of null Sharpes >= observed (one-sided: the claim
    under test is that the strategy beats random direction assignment).
    """
    rng = np.random.default_rng(seed)
    work = df.assign(direction=df[main_direction_col])

    observed_sharpe = _date_aggregated_sharpe(run_backtest(work, exit_horizon=exit_horizon, **backtest_kwargs))

    null_sharpes = np.empty(n_permutations)
    for k in range(n_permutations):
        null_direction = permuted_direction(work, "direction", rng)
        null_result = run_backtest(work.assign(direction=null_direction), exit_horizon=exit_horizon, **backtest_kwargs)
        null_sharpes[k] = _date_aggregated_sharpe(null_result)

    p_value = float((null_sharpes >= observed_sharpe).mean())
    return {"observed_sharpe": observed_sharpe, "null_sharpes": null_sharpes, "p_value": p_value}


def block_bootstrap_sharpe_ci(df, direction_col, exit_horizon, n_boot=1000, seed=0, ci=0.90, **backtest_kwargs):
    """Block bootstrap clustered by scheduled_date: resamples distinct calendar dates WITH
    replacement, keeping every event within a resampled date together as one block (respects the
    same-day-shock clustering already established elsewhere in this project, rather than treating
    events as independent draws). Per-date net_pnl only needs computing once (it doesn't depend on
    which bootstrap draw a date lands in, since position sizing/cost/return are fixed given
    ticker+date+direction); each draw then resamples those fixed per-date totals and recomputes
    the annualized Sharpe. Returns {observed_sharpe, boot_sharpes, lo, hi}, `lo`/`hi` the requested
    percentile CI (e.g. 5th/95th for ci=0.90) of the bootstrap distribution.
    """
    rng = np.random.default_rng(seed)
    work = df.assign(direction=df[direction_col])
    result = run_backtest(work, exit_horizon=exit_horizon, **backtest_kwargs)

    daily_pnl = aggregate_by_date(result["net_pnl"], result["scheduled_date"])
    daily_events_per_year = dates_per_year(result["scheduled_date"])
    observed_sharpe = annualized_sharpe(daily_pnl, daily_events_per_year)

    daily_values = daily_pnl.to_numpy()
    boot_sharpes = np.empty(n_boot)
    for k in range(n_boot):
        sample = rng.choice(daily_values, size=len(daily_values), replace=True)
        boot_sharpes[k] = annualized_sharpe(pd.Series(sample), daily_events_per_year)

    alpha = (1 - ci) / 2
    lo, hi = np.quantile(boot_sharpes, [alpha, 1 - alpha])
    return {"observed_sharpe": observed_sharpe, "boot_sharpes": boot_sharpes, "lo": float(lo), "hi": float(hi)}
