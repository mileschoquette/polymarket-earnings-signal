"""Volatility-targeted backtest of the divergence signal. Position size scales inversely with a
ticker's trailing realized vol so every trade targets the same daily P&L variance; trailing vol
uses only strictly-prior price history (no look-ahead), and a missing/degenerate vol estimate
forces zero exposure rather than falling back to a default size.
"""
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

YFINANCE_DIR = Path(__file__).resolve().parents[2] / "data" / "raw" / "yfinance"

_RETURN_COL = {"t_plus_1": "return_t_plus_1", "t_plus_5": "return_t_plus_5"}


@lru_cache(maxsize=None)
def _default_price_loader(ticker):
    """Close price series for `ticker`, indexed by date, from data/raw/yfinance/<ticker>.parquet."""
    return pd.read_parquet(YFINANCE_DIR / f"{ticker}.parquet")["Close"]


def trailing_realized_vol(ticker, entry_date, window=20, price_loader=None):
    """Std of daily log returns over the `window` trading days strictly before entry_date (never
    including entry_date or anything after it). None if fewer than window + 1 prior price points
    exist (window+1 prices are needed to form window returns).
    """
    loader = price_loader or _default_price_loader
    closes = loader(ticker)

    target = pd.Timestamp(entry_date)
    if closes.index.tz is not None:
        target = target.tz_localize(closes.index.tz) if target.tz is None else target.tz_convert(closes.index.tz)

    prior = closes[closes.index < target]
    if len(prior) < window + 1:
        return None

    prior = prior.iloc[-(window + 1):]
    log_returns = np.log(prior / prior.shift(1)).dropna()
    return log_returns.std(ddof=1)


def run_backtest(df, exit_horizon="t_plus_1", cost_bps=5, target_daily_vol=0.02,
                  max_leverage=3.0, min_leverage=0.1, price_loader=None):
    """df must already have a `direction` column (from compute_signal). Returns a DataFrame with
    the identifying columns plus position_size, gross_return, cost, net_pnl per event.
    """
    return_col = _RETURN_COL[exit_horizon]
    id_cols = [c for c in ("event_id", "ticker", "scheduled_date", "direction") if c in df.columns]

    rows = []
    for _, row in df.iterrows():
        direction = row["direction"]
        ret = row[return_col]

        if direction == 0 or pd.isna(ret):
            position_size = gross_return = cost = net_pnl = 0.0
        else:
            vol = trailing_realized_vol(row["ticker"], row["scheduled_date"], price_loader=price_loader)
            if vol is None or vol <= 0:
                position_size = gross_return = cost = net_pnl = 0.0
            else:
                position_size = float(np.clip(target_daily_vol / vol, min_leverage, max_leverage))
                gross_return = direction * position_size * ret
                cost = position_size * (cost_bps / 10000) * 2
                net_pnl = gross_return - cost

        rows.append({
            **{c: row[c] for c in id_cols},
            "position_size": position_size,
            "gross_return": gross_return,
            "cost": cost,
            "net_pnl": net_pnl,
        })

    return pd.DataFrame(rows)
