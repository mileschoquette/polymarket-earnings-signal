"""Driver for the event-reaction stage: does the stock already move in the direction of the
market's later-observed implied-probability momentum before the earnings print, or is it
efficient right up to the announcement? Builds car_pre (market-adjusted pre-announcement
abnormal return) for every panel row, regresses it on implied_prob_momentum with cluster-robust
inference, and saves a scatter of the fit.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.analysis.event_reaction import build_car_pre, fit_car_regression

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "earnings_panel.parquet"
FIGURES_DIR = Path(__file__).resolve().parents[1] / "paper" / "figures"
BLUE = "#2a78d6"  # single-series categorical slot 1, validated in dataviz palette
GRAY = "#52514e"  # muted reference-line ink, validated in dataviz palette


def plot_car_vs_momentum(df, result, out_dir):
    """Scatter of implied_prob_momentum vs car_pre with the fitted OLS line overlaid."""
    valid = df.dropna(subset=["car_pre", "implied_prob_momentum"])
    x = valid["implied_prob_momentum"]
    x_line = np.linspace(x.min(), x.max(), 100)
    y_line = result.params["const"] + result.params["implied_prob_momentum"] * x_line

    fig, ax = plt.subplots(figsize=(7, 6))
    ax.scatter(x, valid["car_pre"], color=BLUE, alpha=0.5, s=18, label="Event")
    ax.plot(x_line, y_line, color=GRAY, linestyle="--", linewidth=2, label="Fitted OLS line")
    ax.axhline(0, color=GRAY, linewidth=0.75, alpha=0.5)
    ax.axvline(0, color=GRAY, linewidth=0.75, alpha=0.5)
    ax.set_xlabel("Implied-probability momentum (T-5d -> T-1d)")
    ax.set_ylabel("Pre-announcement CAR (T-5d -> T-1d, market-adjusted)")
    ax.set_title("Pre-announcement stock reaction vs implied-probability momentum")
    ax.legend(frameon=False, loc="best")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(out_dir / "car_vs_momentum.png", dpi=150)
    plt.close(fig)


def main():
    df = pd.read_parquet(DATA_PATH)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    df = build_car_pre(df)
    n_total = len(df)
    n_car = df["car_pre"].notna().sum()
    print(f"car_pre available: {n_car}/{n_total} rows ({100 * n_car / n_total:.1f}%)")

    result = fit_car_regression(df)
    coef = result.params["implied_prob_momentum"]
    se = result.bse["implied_prob_momentum"]
    p_value = result.pvalues["implied_prob_momentum"]
    n = int(result.nobs)

    print("\nOLS: car_pre ~ implied_prob_momentum (SEs clustered by scheduled_date)")
    print(f"coefficient: {coef:.4f}")
    print(f"std error:   {se:.4f}")
    print(f"p-value:     {p_value:.4f}")
    print(f"n:           {n}")

    plot_car_vs_momentum(df, result, FIGURES_DIR)
    print(f"\nSaved figure to {FIGURES_DIR / 'car_vs_momentum.png'}")


if __name__ == "__main__":
    main()
