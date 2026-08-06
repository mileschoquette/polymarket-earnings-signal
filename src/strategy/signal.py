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


def compute_signal(df, threshold_sd=0.5, min_history=20):
    """Adds `divergence` and `direction` (-1/0/1) columns to a copy of df, sorted by
    scheduled_date. direction[i] is +1/-1 only once |divergence| exceeds threshold_sd times the
    expanding standard deviation of strictly-prior events' divergence values (never the
    full-sample std, which would leak future information into a signal applied to past events),
    and only once at least min_history such prior observations exist. Rows with a null
    divergence are skipped (direction stays 0).
    """
    out = df.sort_values("scheduled_date", kind="stable").reset_index(drop=True).copy()
    out["divergence"] = compute_divergence(out)
    direction = [0] * len(out)

    prior_divergences = []
    for _, idx_iter in groupby(range(len(out)), key=lambda i: out.loc[i, "scheduled_date"]):
        day_idx = list(idx_iter)
        day_values = []

        for i in day_idx:
            div = out.loc[i, "divergence"]
            if pd.isna(div):
                continue
            if len(prior_divergences) >= min_history:
                threshold = threshold_sd * np.std(prior_divergences, ddof=1)
                if div > threshold:
                    direction[i] = 1
                elif div < -threshold:
                    direction[i] = -1
            day_values.append(div)

        # Update expanding state only after scoring every event on this date.
        prior_divergences.extend(day_values)

    out["direction"] = direction
    return out
