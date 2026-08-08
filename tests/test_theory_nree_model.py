import numpy as np

from src.theory.nree_model import (
    expected_brier_gap,
    expected_divergence_profit_components,
    informed_trading_coefficient,
    posterior_variance,
    resolved_variance_fraction,
)


def test_tau_goes_to_zero_as_beta_shrinks():
    tau = resolved_variance_fraction(beta=1e-6, sigma_theta2=0.01, sigma_eps2=0.02, sigma_u2=0.05)
    assert tau < 1e-6


def test_tau_goes_to_one_in_noiseless_limit():
    tau = resolved_variance_fraction(beta=1.0, sigma_theta2=0.01, sigma_eps2=1e-12, sigma_u2=1e-12)
    assert abs(tau - 1.0) < 1e-6


def test_lambda_and_tau_hand_computed():
    # beta=2, sigma_theta2=0.01, sigma_eps2=0.02, sigma_u2=0.05
    # denominator = 4*(0.01+0.02) + 0.05 = 0.12 + 0.05 = 0.17
    # lambda = 2*0.01/0.17 = 0.02/0.17
    beta, sigma_theta2, sigma_eps2, sigma_u2 = 2.0, 0.01, 0.02, 0.05
    lam = informed_trading_coefficient(beta, sigma_theta2, sigma_eps2, sigma_u2)
    assert abs(lam - 0.02 / 0.17) < 1e-12
    tau = resolved_variance_fraction(beta, sigma_theta2, sigma_eps2, sigma_u2)
    assert abs(tau - lam * beta) < 1e-12
    assert abs(tau - (0.02 / 0.17) * 2.0) < 1e-12


def test_posterior_variance_and_brier_gap_hand_computed():
    sigma_theta2, tau = 0.01, 0.4
    assert abs(posterior_variance(sigma_theta2, tau) - 0.006) < 1e-12
    assert abs(expected_brier_gap(sigma_theta2, tau) - 0.004) < 1e-12
    # the two must sum back to sigma_theta2 exactly (variance reduction identity)
    assert abs(posterior_variance(sigma_theta2, tau) + expected_brier_gap(sigma_theta2, tau) - sigma_theta2) < 1e-12


def _simulate_panel(beta, sigma_theta2, sigma_eps2, sigma_u2, n, seed):
    """theta, eps, u ~ independent Gaussians (deviation-from-prior frame, pi=0 WLOG); X and the
    price p = lambda*X follow the model's linear pricing rule exactly.
    """
    rng = np.random.default_rng(seed)
    theta = rng.normal(0, np.sqrt(sigma_theta2), n)
    eps = rng.normal(0, np.sqrt(sigma_eps2), n)
    u = rng.normal(0, np.sqrt(sigma_u2), n)
    x = beta * (theta + eps) + u
    lam = informed_trading_coefficient(beta, sigma_theta2, sigma_eps2, sigma_u2)
    p = lam * x
    return theta, p


def test_monte_carlo_posterior_variance_matches_proposition_1():
    beta, sigma_theta2, sigma_eps2, sigma_u2 = 1.5, 0.02, 0.03, 0.08
    n = 200_000
    theta, p = _simulate_panel(beta, sigma_theta2, sigma_eps2, sigma_u2, n, seed=0)

    tau = resolved_variance_fraction(beta, sigma_theta2, sigma_eps2, sigma_u2)
    expected = posterior_variance(sigma_theta2, tau)

    # p is the exact linear MMSE projection of theta (coefficient 1, intercept 0 in this frame),
    # so the residual theta - p is the empirical analog of theta | p, without needing a separate
    # regression step.
    empirical = np.var(theta - p)
    # Monte Carlo SE of a variance estimate from n draws is roughly sqrt(2/n) * true_variance;
    # use a comfortable 6-sigma tolerance so this is not flaky but still catches a real bug.
    mc_se = np.sqrt(2.0 / n) * expected
    assert abs(empirical - expected) < 6 * mc_se


def test_monte_carlo_zero_expected_profit_matches_proposition_3():
    beta, sigma_theta2, sigma_eps2, sigma_u2 = 1.5, 0.02, 0.03, 0.08
    n = 200_000
    theta, p = _simulate_panel(beta, sigma_theta2, sigma_eps2, sigma_u2, n, seed=1)

    # (p - pi) * (theta - p) with pi = 0 in this deviation frame
    profit = p * (theta - p)
    empirical_mean = profit.mean()
    mc_se = profit.std(ddof=1) / np.sqrt(n)
    # 6-sigma band around the analytically-exact zero: would catch a sign error, not just noise.
    assert abs(empirical_mean) < 6 * mc_se


def test_divergence_profit_components_cancel_exactly():
    beta, sigma_theta2, sigma_eps2, sigma_u2 = 1.5, 0.02, 0.03, 0.08
    lam = informed_trading_coefficient(beta, sigma_theta2, sigma_eps2, sigma_u2)
    var_x = beta**2 * (sigma_theta2 + sigma_eps2) + sigma_u2
    components = expected_divergence_profit_components(beta, sigma_theta2, lam, var_x)
    assert set(components) == {"signal_term", "noise_term"}
    assert abs(components["signal_term"] - components["noise_term"]) < 1e-12
