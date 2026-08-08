"""Stylized noisy rational-expectations equilibrium (NREE) model, in the tradition of
Grossman & Stiglitz (1980), Hellwig (1980), and Kyle (1985), connecting Polymarket's price
informativeness to whether trading on that price is expected to be profitable.

Notation (all in the deviation-from-prior frame, i.e. theta = pi* - pi where pi* is the latent
true beat probability and pi is the public prior/historical baseline): an informed sector observes
a private signal s = theta + eps, eps ~ N(0, sigma_eps2); noise/liquidity traders contribute order
flow u ~ N(0, sigma_u2), independent of theta and eps; aggregate order flow is X = beta*(theta+eps)
+ u for informed-trading intensity beta > 0; a competitive market maker prices via the linear
conditional-expectation rule p = lambda * X. tau = lambda*beta in (0, 1) is the fraction of prior
variance resolved by price -- the model's single informativeness parameter.
"""


def informed_trading_coefficient(beta, sigma_theta2, sigma_eps2, sigma_u2):
    """lambda = Cov(theta, X) / Var(X) = beta*sigma_theta2 / (beta**2*(sigma_theta2+sigma_eps2) + sigma_u2)."""
    denominator = beta**2 * (sigma_theta2 + sigma_eps2) + sigma_u2
    return beta * sigma_theta2 / denominator


def resolved_variance_fraction(beta, sigma_theta2, sigma_eps2, sigma_u2):
    """tau = lambda*beta, the fraction of prior variance resolved by price (in (0, 1))."""
    lam = informed_trading_coefficient(beta, sigma_theta2, sigma_eps2, sigma_u2)
    return lam * beta


def posterior_variance(sigma_theta2, tau):
    """Proposition 1: Var(theta | p) = sigma_theta2 * (1 - tau)."""
    return sigma_theta2 * (1 - tau)


def expected_brier_gap(sigma_theta2, tau):
    """Proposition 2: E[Brier(prior)] - E[Brier(price)] = sigma_theta2 * tau, EXACTLY under this
    model's assumptions (not an approximation -- this identity holds for any outcome distribution,
    not just Gaussian, since it is just the posterior-variance reduction from `posterior_variance`
    restated: sigma_theta2 - sigma_theta2*(1-tau) = sigma_theta2*tau).
    """
    return sigma_theta2 * tau


def expected_divergence_profit_components(beta, sigma_theta2, lam, var_x):
    """Proposition 3: E[(p-pi)*(pi*-p)] = signal_term - noise_term, which cancel EXACTLY
    (signal_term = lambda*beta*sigma_theta2 = noise_term = lambda**2*Var(X), since
    lambda = Cov(theta,X)/Var(X) implies lambda*Var(X) = beta*sigma_theta2). Returned separately,
    rather than as a single hard-coded 0.0, so the cancellation itself is testable.
    """
    return {
        "signal_term": lam * beta * sigma_theta2,
        "noise_term": lam**2 * var_x,
    }
