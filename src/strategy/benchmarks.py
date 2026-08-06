"""Benchmark strategies for the main divergence signal. Each function returns a copy of df with
a `direction` column, ready for `src.strategy.backtest.run_backtest` -- so every benchmark goes
through the identical vol-targeted-sizing/cost/P&L machinery as the main strategy, which is what
makes the comparison to it fair.
"""
import numpy as np
import pandas as pd

from src.strategy.signal import expanding_threshold_direction


def buy_and_hold_direction(df):
    """direction = 1 for every row: always long, no signal at all. Isolates whether the main
    strategy's long/short/flat selection adds value beyond just being long every stock going into
    its earnings print.
    """
    out = df.copy()
    out["direction"] = 1
    return out


def historical_only_direction(df, threshold_sd=0.5, min_history=20):
    """Same expanding, no-lookahead threshold construction as compute_signal (shared via
    expanding_threshold_direction), but thresholding `historical_beat_rate - 0.5` instead of
    `implied_prob_pre_earnings - historical_beat_rate`. Asks whether firm history alone (no
    market price at all) would look profitable under a similarly constructed threshold rule --
    if so, that undercuts the claim that the market's information drives the main strategy's
    returns.
    """
    out = df.sort_values("scheduled_date", kind="stable").reset_index(drop=True).copy()
    out["historical_divergence"] = out["historical_beat_rate"] - 0.5
    out["direction"] = expanding_threshold_direction(
        out, out["historical_divergence"], threshold_sd, min_history
    )
    return out


def perfect_foresight_direction(df):
    """direction = 2*actual_beat - 1 (+1 if the company actually beat, -1 if it missed). A sanity
    ceiling built from information not available at trade time -- not a real competitor, and
    should be labeled as such wherever reported.
    """
    out = df.copy()
    out["direction"] = 2 * out["actual_beat"] - 1
    return out


def permuted_direction(df, direction_col, rng):
    """Randomly permutes the SIGN of nonzero entries in df[direction_col] across events: which
    events are flat (0) is untouched, and the count of +1s/-1s (and, since direction never carries
    magnitude, position sizing/dates) is preserved exactly -- only which traded events get +1 vs
    -1 is scrambled. `rng` is a numpy.random.Generator, for reproducibility. Returns a new Series.
    """
    direction = df[direction_col].to_numpy().copy()
    nonzero_mask = direction != 0
    direction[nonzero_mask] = rng.permutation(direction[nonzero_mask])
    return pd.Series(direction, index=df.index, name=direction_col)
