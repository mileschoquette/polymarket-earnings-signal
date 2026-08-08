"""Driver for the calibration-and-encompassing stage. Covers the calibration half: Brier score
comparison of Polymarket's implied probability against the historical-beat-rate baseline, the
Murphy decomposition, and a reliability diagram. Also covers the encompassing regression: does
the implied probability's level and pre-print momentum add information beyond historical_beat_rate
in a logit model, tested with a nested likelihood-ratio test and cluster-robust inference.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from src.analysis.calibration import bootstrap_brier_gap_ci, brier_decomposition, compare_forecasts
from src.analysis.encompassing import (
    build_sample,
    cluster_robustness_checks,
    fit_full,
    fit_restricted,
    likelihood_ratio_test,
    single_predictor_dominance,
    summarize_full_model,
)

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "earnings_panel.parquet"
FIGURES_DIR = Path(__file__).resolve().parents[1] / "paper" / "figures"
BLUE = "#2a78d6"  # single-series categorical slot 1, validated in dataviz palette
GRAY = "#52514e"  # muted reference-line ink, validated in dataviz palette


def _print_section(title, obj):
    print(f"\n{'=' * len(title)}\n{title}\n{'=' * len(title)}")
    print(obj)


def plot_reliability_diagram(bin_table, out_dir):
    """Mean predicted probability vs realized frequency per bin, against the 45-degree
    perfect-calibration reference line.
    """
    valid = bin_table.dropna(subset=["mean_predicted", "mean_realized"])
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot([0, 1], [0, 1], color=GRAY, linestyle="--", linewidth=1.5, label="Perfect calibration")
    ax.plot(
        valid["mean_predicted"], valid["mean_realized"], color=BLUE, marker="o", markersize=8,
        linewidth=2, label="Implied beat probability",
    )
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("Mean predicted probability (bin)")
    ax.set_ylabel("Realized beat frequency (bin)")
    ax.set_title("Reliability diagram: Polymarket implied beat probability")
    ax.legend(frameon=False, loc="upper left")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(out_dir / "reliability_diagram.png", dpi=150)
    plt.close(fig)


def run_encompassing_regression(df):
    """Fits the restricted (historical_beat_rate-only) and full (+ implied level and momentum)
    logit models on the same listwise-deleted sample, and reports the full model's inference
    under three clustering variants, the nested LR test, and the single-predictor dominance check.
    """
    sample = build_sample(df)
    restricted = fit_restricted(sample)
    full_by_date = fit_full(sample, cluster_col="scheduled_date")

    _print_section("Full model coefficients, SEs, z, p (clustered by scheduled_date -- primary spec)",
                    summarize_full_model(full_by_date))

    checks = cluster_robustness_checks(sample)
    _print_section("Full model coefficients, SEs, z, p (clustered by ticker -- robustness)",
                    summarize_full_model(checks["by_ticker"]))

    twoway = checks["twoway"]
    twoway_table = pd.DataFrame({
        "coef": twoway["params"], "se": twoway["bse"], "z": twoway["z"], "p_value": twoway["p_value"],
    }).loc[["implied_prob_pre_earnings", "implied_prob_momentum"]]
    _print_section(
        "Full model coefficients, SEs, z, p (two-way CGM cluster, date x ticker -- robustness)", twoway_table,
    )

    lr = likelihood_ratio_test(restricted, full_by_date)
    _print_section(
        "Likelihood-ratio test: full model vs historical_beat_rate-only (H0: c=d=0, 2 df)", lr,
    )

    dominance = single_predictor_dominance(sample)
    dominance_summary = {
        "historical_beat_rate_only_llf": dominance["historical_only"].llf,
        "historical_beat_rate_only_pseudo_r2": dominance["historical_only"].prsquared,
        "implied_prob_pre_earnings_only_llf": dominance["implied_only"].llf,
        "implied_prob_pre_earnings_only_pseudo_r2": dominance["implied_only"].prsquared,
        "dominant_single_predictor": dominance["dominant"],
    }
    _print_section("Chong-Hendry-style single-predictor dominance check", dominance_summary)

    _print_section("Final sample size used for the encompassing regression", {"n": len(sample)})


def main():
    df = pd.read_parquet(DATA_PATH)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    comparison = compare_forecasts(df["implied_prob_pre_earnings"], df["historical_beat_rate"], df["actual_beat"])
    _print_section("Paired Brier score: implied probability vs historical baseline", comparison)

    gap_ci = bootstrap_brier_gap_ci(
        df["implied_prob_pre_earnings"], df["historical_beat_rate"], df["actual_beat"], df["scheduled_date"],
    )
    _print_section(
        "Block-bootstrap 90% CI on the Brier gap (historical - implied), clustered by scheduled_date",
        {"observed_gap": gap_ci["observed_gap"], "lo": gap_ci["lo"], "hi": gap_ci["hi"]},
    )

    decomp = brier_decomposition(df["implied_prob_pre_earnings"], df["actual_beat"])
    summary = {k: v for k, v in decomp.items() if k != "bin_table"}
    _print_section("Brier decomposition for implied_prob_pre_earnings", summary)
    _print_section("Reliability diagram bin table", decomp["bin_table"])

    plot_reliability_diagram(decomp["bin_table"], FIGURES_DIR)
    print(f"\nSaved figure to {FIGURES_DIR / 'reliability_diagram.png'}")

    # Same paired non-null subsample compare_forecasts/bootstrap_brier_gap_ci use above (n=1,216),
    # not the full df, so this decomposition's uncertainty term matches decomp's exactly and the
    # two are directly comparable for the theory section's corollary.
    paired = df.dropna(subset=["implied_prob_pre_earnings", "historical_beat_rate"])
    decomp_price_paired = brier_decomposition(paired["implied_prob_pre_earnings"], paired["actual_beat"])
    decomp_prior_paired = brier_decomposition(paired["historical_beat_rate"], paired["actual_beat"])
    _print_section(
        "Brier decomposition, implied_prob_pre_earnings vs historical_beat_rate, same n=1,216 paired sample "
        "(for the theory-section corollary)",
        {
            "price_reliability": decomp_price_paired["reliability"],
            "price_resolution": decomp_price_paired["resolution"],
            "prior_reliability": decomp_prior_paired["reliability"],
            "prior_resolution": decomp_prior_paired["resolution"],
            "exact_gap_via_resolution_minus_reliability": (
                (decomp_price_paired["resolution"] - decomp_price_paired["reliability"])
                - (decomp_prior_paired["resolution"] - decomp_prior_paired["reliability"])
            ),
            "direct_brier_gap": comparison["brier_historical"] - comparison["brier_implied"],
        },
    )

    run_encompassing_regression(df)


if __name__ == "__main__":
    main()
