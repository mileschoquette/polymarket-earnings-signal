"""Event-reaction (cumulative abnormal return) analysis: does the stock already start moving in
the direction of the market's later-observed implied-probability momentum before the earnings
print, or is it efficient right up to the announcement? Complements the encompassing regression,
which found implied_prob_momentum does not significantly predict actual_beat -- this asks a
different question: whether the equity price itself pre-empts that momentum, independent of
whether the momentum is genuinely informative about the outcome.
"""
from pathlib import Path

import pandas as pd
import statsmodels.api as sm
import yaml

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
YFINANCE_DIR = DATA_DIR / "raw" / "yfinance"
_config = yaml.safe_load((Path(__file__).resolve().parents[2] / "config" / "earnings_config.yaml").read_text())
MOMENTUM_DAYS = _config["features"]["momentum_window_days"]  # e.g. [5, 1] -> T-5d, T-1d, same window as implied_prob_momentum

_price_cache = {}


def _load_closes(ticker):
    """Cached daily close series for a ticker, or None if its yfinance parquet is missing (mirrors merge_panel._load_closes)."""
    if ticker not in _price_cache:
        path = YFINANCE_DIR / f"{ticker}.parquet"
        _price_cache[ticker] = pd.read_parquet(path)["Close"] if path.exists() else None
    return _price_cache[ticker]


def _close_at_or_before(closes, target):
    """Most recent close at or before target, or None if no such point exists (mirrors
    merge_panel.stock_reaction's tz handling, but inclusive of target itself -- same "at or
    before" convention build_features.py uses for the implied-probability snapshots).
    """
    if closes.index.tz is not None:
        target = target.tz_localize(closes.index.tz)
    at_or_before = closes[closes.index <= target]
    return at_or_before.iloc[-1] if not at_or_before.empty else None


def pre_announcement_return(ticker, scheduled_date):
    """Return from the T-far snapshot close to the T-near snapshot close (same day offsets as
    implied_prob_momentum, e.g. T-5d -> T-1d before scheduled_date), each using the most recent
    close at or before its target date. None if the ticker's parquet or either price point is
    unavailable.
    """
    closes = _load_closes(ticker)
    if closes is None:
        return None
    far_days, near_days = max(MOMENTUM_DAYS), min(MOMENTUM_DAYS)
    day = pd.Timestamp(scheduled_date)
    p_far = _close_at_or_before(closes, day - pd.Timedelta(days=far_days))
    p_near = _close_at_or_before(closes, day - pd.Timedelta(days=near_days))
    if p_far is None or p_near is None:
        return None
    return p_near / p_far - 1


def car_pre(ticker, scheduled_date):
    """Pre-announcement cumulative abnormal return: the stock's pre-announcement return (T-far to
    T-near) minus SPY's return over the identical window. This is a simple market-adjusted
    return, not a full market-model (beta-adjusted) abnormal return -- a standard simplifying
    convention in event studies, named explicitly here rather than presented as more
    sophisticated than it is. None if either leg is unavailable.
    """
    stock_ret = pre_announcement_return(ticker, scheduled_date)
    market_ret = pre_announcement_return("SPY", scheduled_date)
    if stock_ret is None or market_ret is None:
        return None
    return stock_ret - market_ret


def build_car_pre(df):
    """Adds a car_pre column to df, one value per (ticker, scheduled_date) row. Left as NaN where
    the ticker's cached price parquet or a required price point is unavailable.
    """
    df = df.copy()
    df["car_pre"] = [car_pre(t, d) for t, d in zip(df["ticker"], df["scheduled_date"])]
    return df


def fit_car_regression(df, cluster_col="scheduled_date"):
    """OLS of car_pre on implied_prob_momentum, with cluster-robust SEs by cluster_col (same
    clustering rationale as the encompassing regression -- same-day reporters share market-wide
    shocks). Listwise-deletes rows missing car_pre, implied_prob_momentum, or cluster_col.
    """
    sample = df.dropna(subset=["car_pre", "implied_prob_momentum", cluster_col])
    y = sample["car_pre"].astype(float)
    X = sm.add_constant(sample["implied_prob_momentum"].astype(float))
    groups = sample[cluster_col].values
    return sm.OLS(y, X).fit(cov_type="cluster", cov_kwds={"groups": groups})
