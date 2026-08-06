"""Calibration analysis: Brier score, the Murphy (1973) reliability/resolution/uncertainty
decomposition, and a paired comparison of the implied-probability forecast against the
historical-beat-rate baseline.
"""
import numpy as np
import pandas as pd


def brier_score(probs, outcomes):
    """Mean squared forecast error, dropping pairs where probs is null."""
    probs = np.asarray(probs, dtype=float)
    outcomes = np.asarray(outcomes, dtype=float)
    mask = ~np.isnan(probs)
    return float(np.mean((probs[mask] - outcomes[mask]) ** 2))


def brier_decomposition(probs, outcomes, n_bins=10):
    """Murphy (1973) decomposition: brier_score = reliability - resolution + uncertainty.
    Bins predictions into n_bins equal-width buckets over [0, 1]. Returns a dict with the three
    terms, the reconstructed brier score, and a per-bin table for a reliability diagram.
    """
    probs = np.asarray(probs, dtype=float)
    outcomes = np.asarray(outcomes, dtype=float)
    mask = ~np.isnan(probs)
    probs, outcomes = probs[mask], outcomes[mask]

    edges = np.linspace(0, 1, n_bins + 1)
    bin_idx = pd.cut(probs, bins=edges, include_lowest=True, labels=False)

    n = len(probs)
    ybar = outcomes.mean()
    uncertainty = ybar * (1 - ybar)

    rows = []
    reliability = 0.0
    resolution = 0.0
    for b in range(n_bins):
        in_bin = bin_idx == b
        count = int(in_bin.sum())
        lo, hi = edges[b], edges[b + 1]
        row = {
            "bin": b, "low": lo, "high": hi, "midpoint": (lo + hi) / 2, "count": count,
            "mean_predicted": np.nan, "mean_realized": np.nan,
        }
        if count > 0:
            mean_pred = probs[in_bin].mean()
            mean_real = outcomes[in_bin].mean()
            weight = count / n
            reliability += weight * (mean_pred - mean_real) ** 2
            resolution += weight * (mean_real - ybar) ** 2
            row["mean_predicted"] = mean_pred
            row["mean_realized"] = mean_real
        rows.append(row)

    return {
        "reliability": reliability,
        "resolution": resolution,
        "uncertainty": uncertainty,
        "brier_score": reliability - resolution + uncertainty,
        "bin_table": pd.DataFrame(rows),
    }


def compare_forecasts(implied_prob, historical_rate, outcomes):
    """Paired Brier-score comparison of implied_prob vs historical_rate as forecasts of outcomes,
    restricted to the subset of rows where both forecasts are non-null.
    """
    implied = np.asarray(implied_prob, dtype=float)
    historical = np.asarray(historical_rate, dtype=float)
    outcomes = np.asarray(outcomes, dtype=float)
    mask = ~np.isnan(implied) & ~np.isnan(historical)
    return {
        "n": int(mask.sum()),
        "brier_implied": brier_score(implied[mask], outcomes[mask]),
        "brier_historical": brier_score(historical[mask], outcomes[mask]),
    }
