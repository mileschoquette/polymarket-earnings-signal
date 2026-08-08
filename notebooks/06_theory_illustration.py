"""Driver for the theoretical-framework illustration: builds the main t+1 divergence-signal
backtest exactly as notebooks/05_backtest_results.py does, then compares the observed Sharpe's
sampling uncertainty against Lo (2002)'s analytic standard error and a Monte Carlo null-hypothesis
distribution calibrated to this backtest's own date-aggregated P&L, alongside the block-bootstrap CI
already used as the paper's primary uncertainty estimate.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import norm

from src.strategy.backtest import run_backtest
from src.strategy.performance import aggregate_by_date, annualized_sharpe, dates_per_year
from src.strategy.signal import compute_signal
from src.strategy.significance import block_bootstrap_sharpe_ci
from src.theory.sharpe_sampling import lo_2002_se, simulate_null_sharpe_distribution

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "earnings_panel.parquet"
FIGURES_DIR = Path(__file__).resolve().parents[1] / "paper" / "figures"
BLUE = "#2a78d6"  # categorical slot 1, validated in dataviz palette (simulated null distribution)
ORANGE = "#eb6834"  # categorical slot 2, validated in dataviz palette (observed Sharpe marker)
GRAY = "#52514e"  # muted reference-line ink, validated in dataviz palette (Lo SE curve, bootstrap CI)


def plot_null_sharpe_distribution(null_sharpes, lo_se, observed_sharpe, boot_lo, boot_hi, out_dir):
    """Histogram of the simulated null-hypothesis Sharpe distribution, Lo's analytic SE overlaid
    as a normal curve, the observed Sharpe marked, and the block-bootstrap 90% CI bounds marked.
    """
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.hist(null_sharpes, bins=60, density=True, color=BLUE, alpha=0.55,
            label="Simulated null distribution (H0: true Sharpe = 0)")

    x = np.linspace(null_sharpes.min(), null_sharpes.max(), 300)
    ax.plot(x, norm.pdf(x, loc=0, scale=lo_se), color=GRAY, linewidth=2,
            label=f"Lo (2002) normal approximation (SE={lo_se:.3f})")

    ax.axvline(observed_sharpe, color=ORANGE, linewidth=2, label=f"Observed Sharpe ({observed_sharpe:.3f})")
    ax.axvline(boot_lo, color=GRAY, linewidth=1.25, linestyle="--", label="Block-bootstrap 90% CI")
    ax.axvline(boot_hi, color=GRAY, linewidth=1.25, linestyle="--")

    ax.set_xlabel("Annualized Sharpe ratio")
    ax.set_ylabel("Density")
    ax.set_title("Sampling uncertainty of the observed Sharpe under the model's null")
    ax.legend(frameon=False, loc="upper left", fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(out_dir / "null_sharpe_distribution.png", dpi=150)
    plt.close(fig)


def main():
    df = pd.read_parquet(DATA_PATH)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    signal_df = compute_signal(df)
    result = run_backtest(signal_df, exit_horizon="t_plus_1")

    daily_pnl = aggregate_by_date(result["net_pnl"], result["scheduled_date"])
    daily_pnl_std = daily_pnl.std(ddof=1)
    n_dates = len(daily_pnl)
    periods_per_year = dates_per_year(result["scheduled_date"])
    observed_sharpe = annualized_sharpe(daily_pnl, periods_per_year)

    print("=== Backtest inputs (t+1, date-aggregated) ===")
    print(f"n_dates: {n_dates}")
    print(f"periods_per_year: {periods_per_year:.3f}")
    print(f"daily_pnl_std: {daily_pnl_std:.5f}")
    print(f"observed annualized Sharpe: {observed_sharpe:.4f}")

    se = lo_2002_se(observed_sharpe, n_dates, periods_per_year)
    print("\n=== Lo (2002) analytic SE (properly annualized) ===")
    print(f"SE: {se:.4f}")

    null_sharpes = simulate_null_sharpe_distribution(daily_pnl_std, n_dates, periods_per_year, n_sim=5000, seed=0)
    print("\n=== Monte Carlo null-Sharpe distribution (n_sim=5000, seed=0) ===")
    print(f"mean: {null_sharpes.mean():.4f}")
    print(f"std:  {null_sharpes.std(ddof=1):.4f}")

    boot = block_bootstrap_sharpe_ci(signal_df, "direction", "t_plus_1", n_boot=1000, seed=0, ci=0.90)
    print("\n=== Block-bootstrap 90% CI (t+1, same as notebooks/05_backtest_results.py) ===")
    print(f"observed Sharpe (bootstrap's own calc): {boot['observed_sharpe']:.4f}")
    print(f"90% CI: [{boot['lo']:.4f}, {boot['hi']:.4f}]")

    plot_null_sharpe_distribution(null_sharpes, se, observed_sharpe, boot["lo"], boot["hi"], FIGURES_DIR)
    print(f"\nSaved figure to {FIGURES_DIR / 'null_sharpe_distribution.png'}")


if __name__ == "__main__":
    main()
