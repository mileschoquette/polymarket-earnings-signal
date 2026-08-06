"""Trading signal: divergence between the market's implied beat probability and a ticker's own
historical beat rate. Thresholded by an expanding, look-ahead-free standard deviation of prior
divergence values, processed one calendar date at a time (via itertools.groupby, mirroring
src/processing/build_features.py) so same-day events never leak into each other.
"""
from itertools import groupby

import numpy as np
import pandas as pd


def compute_divergence(df):
    """implied_prob_pre_earnings - historical_beat_rate, one value per event."""
    return df["implied_prob_pre_earnings"] - df["historical_beat_rate"]


def expanding_threshold_direction(out, values, threshold_sd=0.5, min_history=20):
    """Shared expanding-std, no-lookahead threshold rule: `out` must already be sorted by
    scheduled_date (stable, reset index), and `values` a Series aligned to out's index holding
    whatever quantity is being thresholded (divergence for the main signal, but any similarly
    constructed quantity for a benchmark). Returns a list of directions (-1/0/1): +1/-1 only once
    |values[i]| exceeds threshold_sd times the expanding standard deviation of strictly-prior
    events' values (never the full-sample std, which would leak future information into a value
    applied to past events), and only once at least min_history such prior observations exist.
    Processed one calendar date at a time (itertools.groupby) so same-day events never leak into
    each other. Rows with a null value are skipped (direction stays 0).
    """
    direction = [0] * len(out)

    prior_values = []
    for _, idx_iter in groupby(range(len(out)), key=lambda i: out.loc[i, "scheduled_date"]):
        day_idx = list(idx_iter)
        day_values = []

        for i in day_idx:
            v = values.loc[i]
            if pd.isna(v):
                continue
            if len(prior_values) >= min_history:
                threshold = threshold_sd * np.std(prior_values, ddof=1)
                if v > threshold:
                    direction[i] = 1
                elif v < -threshold:
                    direction[i] = -1
            day_values.append(v)

        # Update expanding state only after scoring every event on this date.
        prior_values.extend(day_values)

    return direction


def compute_signal(df, threshold_sd=0.5, min_history=20):
    """Adds `divergence` and `direction` (-1/0/1) columns to a copy of df, sorted by
    scheduled_date, via the shared expanding_threshold_direction rule applied to `divergence`.
    """
    out = df.sort_values("scheduled_date", kind="stable").reset_index(drop=True).copy()
    out["divergence"] = compute_divergence(out)
    out["direction"] = expanding_threshold_direction(out, out["divergence"], threshold_sd, min_history)
    return out
