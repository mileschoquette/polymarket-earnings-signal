import numpy as np
import pandas as pd
from scipy.special import expit

from src.analysis.encompassing import (
    build_sample,
    cluster_robustness_checks,
    fit_full,
    fit_restricted,
    likelihood_ratio_test,
    single_predictor_dominance,
)

A_TRUE, B_TRUE, C_TRUE, D_TRUE = -0.2, 0.8, 1.0, 1.5


def _simulate(n, d_true, seed):
    """Simulates historical_beat_rate and implied_prob_pre_earnings as random covariates in
    (0, 1), a planted momentum coefficient d_true, and actual_beat via a Bernoulli draw at the
    true logit-linear probability. scheduled_date/ticker are synthetic grouping labels only (not
    part of the data-generating process) so cluster-robust fits have something to cluster on.
    """
    rng = np.random.default_rng(seed)
    hbr = rng.uniform(0.2, 0.8, n)
    ipe = rng.uniform(0.2, 0.8, n)
    momentum = rng.normal(0, 0.1, n)
    p = expit(A_TRUE + B_TRUE * hbr + C_TRUE * ipe + d_true * momentum)
    actual_beat = rng.binomial(1, p)
    return pd.DataFrame({
        "actual_beat": actual_beat,
        "historical_beat_rate": hbr,
        "implied_prob_pre_earnings": ipe,
        "implied_prob_momentum": momentum,
        "scheduled_date": rng.integers(0, n // 5, n).astype(str),
        "ticker": rng.integers(0, 40, n).astype(str),
    })


def test_full_model_recovers_planted_momentum_coefficient():
    # N=3000 keeps sampling noise small; tolerance is 3 SEs (the fitted estimate's own
    # cluster-robust standard error), the standard "does the CI cover the truth" bar for a single
    # well-powered MLE draw, rather than an arbitrary fixed-width band.
    df = _simulate(n=3000, d_true=D_TRUE, seed=0)
    result = fit_full(df, cluster_col="scheduled_date")
    coef_d = result.params["implied_prob_momentum"]
    se_d = result.bse["implied_prob_momentum"]
    assert abs(coef_d - D_TRUE) < 3 * se_d


def test_full_model_does_not_spuriously_reject_when_true_momentum_is_zero():
    df = _simulate(n=3000, d_true=0.0, seed=1)
    result = fit_full(df, cluster_col="scheduled_date")
    coef_d = result.params["implied_prob_momentum"]
    se_d = result.bse["implied_prob_momentum"]
    ci_lo, ci_hi = coef_d - 1.96 * se_d, coef_d + 1.96 * se_d
    assert ci_lo < 0.0 < ci_hi


def test_likelihood_ratio_test_rejects_when_momentum_and_level_matter():
    df = _simulate(n=3000, d_true=D_TRUE, seed=2)
    sample = build_sample(df)
    restricted = fit_restricted(sample)
    full = fit_full(sample, cluster_col="scheduled_date")
    lr = likelihood_ratio_test(restricted, full)
    assert lr["df"] == 2
    assert lr["lr_stat"] > 0
    assert lr["p_value"] < 0.01


def test_likelihood_ratio_test_same_sample_size_for_restricted_and_full():
    df = _simulate(n=500, d_true=D_TRUE, seed=3)
    df.loc[::10, "implied_prob_momentum"] = np.nan
    sample = build_sample(df)
    restricted = fit_restricted(sample)
    full = fit_full(sample, cluster_col="scheduled_date")
    assert restricted.nobs == full.nobs == len(sample)


def test_build_sample_drops_rows_missing_any_full_model_input():
    df = _simulate(n=100, d_true=D_TRUE, seed=4)
    df.loc[0, "historical_beat_rate"] = np.nan
    df.loc[1, "implied_prob_pre_earnings"] = np.nan
    df.loc[2, "implied_prob_momentum"] = np.nan
    sample = build_sample(df)
    assert len(sample) == 97
    assert sample["historical_beat_rate"].notna().all()
    assert sample["implied_prob_pre_earnings"].notna().all()
    assert sample["implied_prob_momentum"].notna().all()


def test_cluster_robustness_checks_agree_on_point_estimates_across_variants():
    # cov_type only changes the covariance matrix, not the MLE point estimates, so all three
    # clustering variants must return identical coefficients (only SEs should differ).
    df = _simulate(n=800, d_true=D_TRUE, seed=5)
    checks = cluster_robustness_checks(df)
    coef_date = checks["by_date"].params["implied_prob_momentum"]
    coef_ticker = checks["by_ticker"].params["implied_prob_momentum"]
    coef_twoway = checks["twoway"]["params"]["implied_prob_momentum"]
    assert abs(coef_date - coef_ticker) < 1e-8
    assert abs(coef_date - coef_twoway) < 1e-8


def test_single_predictor_dominance_favors_the_more_informative_covariate():
    # Plant a case where implied_prob_pre_earnings is the only real driver of actual_beat and
    # historical_beat_rate is pure noise unrelated to the outcome -- the implied-probability-only
    # model must have higher log-likelihood.
    rng = np.random.default_rng(6)
    n = 2000
    ipe = rng.uniform(0.2, 0.8, n)
    hbr_noise = rng.uniform(0.2, 0.8, n)
    p = expit(-0.5 + 3.0 * ipe)
    df = pd.DataFrame({
        "actual_beat": rng.binomial(1, p),
        "historical_beat_rate": hbr_noise,
        "implied_prob_pre_earnings": ipe,
    })
    result = single_predictor_dominance(df)
    assert result["dominant"] == "implied_prob_pre_earnings"
    assert result["implied_only"].llf > result["historical_only"].llf
