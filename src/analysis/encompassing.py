"""Encompassing regression: does Polymarket's implied beat probability (level and momentum) add
information beyond the historical-beat-rate baseline, in a logit model with valid cluster-robust
inference? Nests historical_beat_rate-only (restricted) inside historical_beat_rate +
implied_prob_pre_earnings + implied_prob_momentum (full), and compares them with a likelihood-ratio
test. Also runs the mirror-image Chong-Hendry-style check: which single-predictor model dominates.
"""
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

FEATURES_RESTRICTED = ["historical_beat_rate"]
FEATURES_FULL = ["historical_beat_rate", "implied_prob_pre_earnings", "implied_prob_momentum"]
REQUIRED_COLS = ["actual_beat"] + FEATURES_FULL + ["scheduled_date", "ticker"]


def build_sample(df):
    """Listwise-deletes rows missing any full-model input, so the restricted and full model are
    fit on the identical sample -- required for a valid nested likelihood-ratio test.
    """
    return df.dropna(subset=REQUIRED_COLS).reset_index(drop=True)


def _fit_logit(df, features, cov_type="nonrobust", cov_kwds=None):
    y = df["actual_beat"].astype(float)
    X = sm.add_constant(df[features].astype(float))
    if cov_type == "nonrobust":
        return sm.Logit(y, X).fit(disp=0)
    return sm.Logit(y, X).fit(disp=0, cov_type=cov_type, cov_kwds=cov_kwds)


def fit_restricted(df, cov_type="nonrobust", cov_kwds=None):
    """logit(P(actual_beat)) = a + b*historical_beat_rate."""
    return _fit_logit(df, FEATURES_RESTRICTED, cov_type=cov_type, cov_kwds=cov_kwds)


def fit_full(df, cluster_col="scheduled_date"):
    """logit(P(actual_beat)) = a + b*historical_beat_rate + c*implied_prob_pre_earnings +
    d*implied_prob_momentum, with SEs clustered by cluster_col (primary spec clusters by
    scheduled_date, since same-day reporters share market-wide shocks).
    """
    groups = df[cluster_col].values
    return _fit_logit(df, FEATURES_FULL, cov_type="cluster", cov_kwds={"groups": groups})


def likelihood_ratio_test(restricted_result, full_result):
    """2*(llf_full - llf_restricted) ~ chi2(df), df = difference in number of slope parameters.
    Valid only when both models are fit on the same sample (enforced by build_sample upstream).
    """
    lr_stat = 2 * (full_result.llf - restricted_result.llf)
    df_diff = int(full_result.df_model - restricted_result.df_model)
    p_value = stats.chi2.sf(lr_stat, df_diff)
    return {"lr_stat": lr_stat, "df": df_diff, "p_value": p_value}


def _twoway_cluster_cov(df):
    """Cameron-Gelbach-Miller two-way cluster covariance: V = V_date + V_ticker - V_intersection,
    where the intersection groups by (scheduled_date, ticker) jointly. Reuses the same MLE fit's
    params for all three pieces (cov_type doesn't change the optimized coefficients, only the
    covariance matrix), so the three V's are directly comparable.
    """
    base = _fit_logit(df, FEATURES_FULL)
    intersection = df["scheduled_date"].astype(str) + "||" + df["ticker"].astype(str)

    v_date = _fit_logit(df, FEATURES_FULL, cov_type="cluster",
                         cov_kwds={"groups": df["scheduled_date"].values}).cov_params()
    v_ticker = _fit_logit(df, FEATURES_FULL, cov_type="cluster",
                           cov_kwds={"groups": df["ticker"].values}).cov_params()
    v_intersection = _fit_logit(df, FEATURES_FULL, cov_type="cluster",
                                 cov_kwds={"groups": intersection.values}).cov_params()

    v_twoway = v_date + v_ticker - v_intersection
    bse = pd.Series(np.sqrt(np.diag(v_twoway)), index=base.params.index)
    z = base.params / bse
    p_value = 2 * stats.norm.sf(np.abs(z))
    return {"params": base.params, "cov_params": v_twoway, "bse": bse, "z": z, "p_value": p_value}


def cluster_robustness_checks(df):
    """Full model fit three ways: clustered by scheduled_date (primary), by ticker (robustness),
    and two-way CGM clustering by both jointly (robustness).
    """
    return {
        "by_date": fit_full(df, cluster_col="scheduled_date"),
        "by_ticker": fit_full(df, cluster_col="ticker"),
        "twoway": _twoway_cluster_cov(df),
    }


def single_predictor_dominance(df):
    """Chong-Hendry-style encompassing check: fits historical_beat_rate alone and
    implied_prob_pre_earnings alone on the same sample, and reports which single-predictor model
    dominates by log-likelihood / McFadden pseudo-R^2.
    """
    historical_only = _fit_logit(df, ["historical_beat_rate"])
    implied_only = _fit_logit(df, ["implied_prob_pre_earnings"])
    dominant = "implied_prob_pre_earnings" if implied_only.llf > historical_only.llf else "historical_beat_rate"
    return {
        "historical_only": historical_only,
        "implied_only": implied_only,
        "dominant": dominant,
    }


def summarize_full_model(result, terms=("implied_prob_pre_earnings", "implied_prob_momentum")):
    """Coefficient, SE, z-stat, and p-value for the requested terms of a fitted full-model result."""
    return pd.DataFrame({
        "coef": result.params[list(terms)],
        "se": result.bse[list(terms)],
        "z": result.tvalues[list(terms)],
        "p_value": result.pvalues[list(terms)],
    })
