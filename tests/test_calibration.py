import numpy as np

from src.analysis.calibration import brier_decomposition, brier_score, compare_forecasts


def _calibrated_dataset():
    """5 buckets of 5 obs each; within each bucket the realized frequency exactly equals the
    predicted probability (0.2 -> 1/5, 0.4 -> 2/5, 0.6 -> 3/5, 0.8 -> 4/5, plus a 1.0/all-beat
    bucket), so this forecast is perfectly calibrated by construction.
    """
    probs, outcomes = [], []
    for p, n_ones in [(0.2, 1), (0.4, 2), (0.6, 3), (0.8, 4), (1.0, 5)]:
        probs += [p] * 5
        outcomes += [1] * n_ones + [0] * (5 - n_ones)
    return np.array(probs), np.array(outcomes)


def _miscalibrated_dataset():
    """100 observations, always predicting 0.9, but the true outcome is a fair coin (50/50)."""
    probs = np.full(100, 0.9)
    outcomes = np.array([1] * 50 + [0] * 50)
    return probs, outcomes


def _mixed_dataset():
    """3 groups at distinct predicted probabilities (0.1, 0.5, 0.9), some well calibrated and
    some not, for a 3rd structurally different case in the reconstruction check.
    """
    probs, outcomes = [], []
    for p, n_ones, count in [(0.1, 2, 20), (0.5, 15, 20), (0.9, 18, 20)]:
        probs += [p] * count
        outcomes += [1] * n_ones + [0] * (count - n_ones)
    return np.array(probs), np.array(outcomes)


def test_brier_score_hand_computable():
    probs = np.array([0.2, 0.8])
    outcomes = np.array([0, 1])
    # (0.2-0)^2 + (0.8-1)^2 = 0.04 + 0.04 -> mean 0.04
    assert abs(brier_score(probs, outcomes) - 0.04) < 1e-12


def test_brier_score_drops_null_probs_instead_of_erroring_or_zeroing():
    probs = np.array([0.2, np.nan, 0.8, None], dtype=float)
    outcomes = np.array([0, 1, 1, 0], dtype=float)
    # only rows 0 and 2 survive: (0.2-0)^2 + (0.8-1)^2 -> mean 0.04
    result = brier_score(probs, outcomes)
    assert abs(result - 0.04) < 1e-12


def test_calibrated_forecast_has_near_zero_reliability():
    probs, outcomes = _calibrated_dataset()
    decomp = brier_decomposition(probs, outcomes, n_bins=5)
    assert abs(decomp["reliability"]) < 1e-9
    assert abs(decomp["brier_score"] - brier_score(probs, outcomes)) < 1e-9


def test_miscalibrated_forecast_has_large_reliability():
    probs, outcomes = _miscalibrated_dataset()
    decomp = brier_decomposition(probs, outcomes, n_bins=10)
    # all mass in the 0.9 bin: reliability = (0.9 - 0.5)^2 = 0.16
    assert abs(decomp["reliability"] - 0.16) < 1e-9

    calibrated_probs, calibrated_outcomes = _calibrated_dataset()
    calibrated_reliability = brier_decomposition(calibrated_probs, calibrated_outcomes, n_bins=5)["reliability"]
    assert decomp["reliability"] > 100 * calibrated_reliability


def test_miscalibrated_reliability_diagram_bin_reflects_mismatch():
    probs, outcomes = _miscalibrated_dataset()
    bin_table = brier_decomposition(probs, outcomes, n_bins=10)["bin_table"]
    occupied = bin_table[bin_table["count"] > 0]
    assert len(occupied) == 1
    row = occupied.iloc[0]
    assert abs(row["mean_predicted"] - 0.9) < 1e-9
    assert abs(row["mean_realized"] - 0.5) < 1e-9


def test_decomposition_reconstructs_brier_score_on_multiple_datasets():
    # Note: the Murphy identity is exact when predictions are constant within each bin (the
    # classic categorical-forecast setup used here); it only holds approximately when
    # predictions vary continuously within a bin, since that introduces a within-bin dispersion
    # residual not captured by the three terms.
    datasets = [_calibrated_dataset(), _miscalibrated_dataset(), _mixed_dataset()]

    for probs, outcomes in datasets:
        decomp = brier_decomposition(probs, outcomes, n_bins=10)
        direct = brier_score(probs, outcomes)
        reconstructed = decomp["reliability"] - decomp["resolution"] + decomp["uncertainty"]
        assert abs(reconstructed - direct) < 1e-9


def test_compare_forecasts_restricts_to_paired_non_null_subset():
    implied = np.array([0.2, np.nan, 0.8, 0.6])
    historical = np.array([0.3, 0.5, np.nan, 0.4])
    outcomes = np.array([0, 1, 1, 0])
    # only index 0 and 3 have both non-null
    result = compare_forecasts(implied, historical, outcomes)
    assert result["n"] == 2
    expected_implied = brier_score(np.array([0.2, 0.6]), np.array([0, 0]))
    expected_historical = brier_score(np.array([0.3, 0.4]), np.array([0, 0]))
    assert abs(result["brier_implied"] - expected_implied) < 1e-12
    assert abs(result["brier_historical"] - expected_historical) < 1e-12
