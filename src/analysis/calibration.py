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


def bootstrap_brier_gap_ci(implied_prob, historical_rate, outcomes, dates, n_boot=1000, seed=0, ci=0.90):
    """Block bootstrap CI on brier_score(historical_rate) - brier_score(implied_prob), restricted
    to rows where both forecasts are non-null. Resamples distinct values of `dates` with
    replacement, pulling in every row that shares a resampled date (same within-date clustering
    rationale as significance.block_bootstrap_sharpe_ci). Returns {observed_gap, boot_gaps, lo,
    hi}, lo/hi the requested percentile CI (e.g. 5th/95th for ci=0.90) of the bootstrap distribution.
    """
    implied = np.asarray(implied_prob, dtype=float)
    historical = np.asarray(historical_rate, dtype=float)
    outcomes = np.asarray(outcomes, dtype=float)
    mask = ~np.isnan(implied) & ~np.isnan(historical)
    implied, historical, outcomes = implied[mask], historical[mask], outcomes[mask]
    dates = pd.Series(dates).to_numpy()[mask]

    def _gap(idx):
        return brier_score(historical[idx], outcomes[idx]) - brier_score(implied[idx], outcomes[idx])

    observed_gap = _gap(np.arange(len(dates)))

    unique_dates = np.unique(dates)
    positions_by_date = {d: np.flatnonzero(dates == d) for d in unique_dates}

    rng = np.random.default_rng(seed)
    boot_gaps = np.empty(n_boot)
    for k in range(n_boot):
        sampled_dates = rng.choice(unique_dates, size=len(unique_dates), replace=True)
        idx = np.concatenate([positions_by_date[d] for d in sampled_dates])
        boot_gaps[k] = _gap(idx)

    alpha = (1 - ci) / 2
    lo, hi = np.quantile(boot_gaps, [alpha, 1 - alpha])
    return {"observed_gap": observed_gap, "boot_gaps": boot_gaps, "lo": float(lo), "hi": float(hi)}


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
