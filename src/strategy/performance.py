"""Performance metrics computed on a per-event net_pnl series (one value per event, chronological).

Event-level Sharpe/Sortino/Calmar annualize by events_per_year, which is only meaningful if events
are roughly independent draws. They aren't here: many events share the same scheduled_date (up to
several dozen same-day reporters in a single earnings-season burst), and same-day events share
market-wide shocks (the same reasoning behind clustering standard errors by date elsewhere in this
project). Treating ~1,200 events/year as ~1,200 independent annual observations overstates the
Sharpe/Sortino/Calmar relative to a conventional time-series annualization. aggregate_by_date sums
same-day contributions into one observation per calendar date before computing performance, which
is the more defensible number for the paper; the raw event-level metrics are still useful as an
upper bound / for comparing horizons, but should be reported alongside the date-aggregated version,
not in place of it.
"""
import numpy as np
import pandas as pd


def aggregate_by_date(pnl, dates):
    """Sums pnl within each scheduled_date into one observation per calendar date (a portfolio
    holding every same-day event simultaneously realizes their summed P&L that day, not N
    separate independent periods). Returns a pandas Series indexed by date, sorted chronologically.
    """
    index = pd.Index(pd.to_datetime(pd.Series(dates).values), name="scheduled_date")
    return pd.Series(pnl.values, index=index).groupby(level=0).sum().sort_index()


def dates_per_year(dates):
    """Average number of distinct calendar dates per year spanned by `dates`, for annualizing the
    date-aggregated performance series (as opposed to events_per_year, which double-counts
    same-day events as if they were independent periods).
    """
    unique_dates = pd.to_datetime(pd.Series(dates).unique())
    span_years = (unique_dates.max() - unique_dates.min()).days / 365.25
    return len(unique_dates) / span_years if span_years > 0 else float("nan")


def annualized_sharpe(pnl, events_per_year):
    """mean(pnl) / std(pnl) * sqrt(events_per_year); 0.0 if std is 0."""
    std = pnl.std(ddof=1)
    if std == 0:
        return 0.0
    return pnl.mean() / std * np.sqrt(events_per_year)


def sortino_ratio(pnl, events_per_year):
    """Like annualized_sharpe but the denominator is the downside deviation (std of negative
    pnl values only). NaN if fewer than 2 negative values.
    """
    downside = pnl[pnl < 0]
    if len(downside) < 2:
        return float("nan")
    downside_std = downside.std(ddof=1)
    if downside_std == 0:
        return float("nan")
    return pnl.mean() / downside_std * np.sqrt(events_per_year)


def max_drawdown(pnl):
    """Most negative value of (cumulative equity - running max of cumulative equity so far),
    where cumulative equity is the cumulative SUM (not product) of pnl. These are risk-scaled
    per-event contributions, not compounded capital, so summing rather than compounding is the
    appropriate simplification here.
    """
    cum = pnl.cumsum()
    return (cum - cum.cummax()).min()


def hit_rate(pnl, executed):
    """Fraction of executed rows (executed=True, i.e. position_size > 0) with net_pnl > 0.
    Pass position_size > 0 here, not direction != 0 -- a nonzero direction whose trailing vol was
    unavailable still gets position_size 0 and net_pnl exactly 0 in run_backtest, and counting
    those zero-P&L placeholders as non-hits understates the real hit rate on trades that actually
    executed.
    """
    return (pnl[executed] > 0).mean()


def calmar_ratio(pnl, events_per_year):
    """Annualized mean return divided by the absolute max drawdown."""
    dd = max_drawdown(pnl)
    if dd == 0:
        return float("nan")
    return (pnl.mean() * events_per_year) / abs(dd)
