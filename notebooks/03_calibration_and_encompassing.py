"""Driver for the calibration-and-encompassing stage. Currently covers the calibration half:
Brier score comparison of Polymarket's implied probability against the historical-beat-rate
baseline, the Murphy decomposition, and a reliability diagram. The encompassing regression is
added to this same file by a later step.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from src.analysis.calibration import brier_decomposition, compare_forecasts

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


def main():
    df = pd.read_parquet(DATA_PATH)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    comparison = compare_forecasts(df["implied_prob_pre_earnings"], df["historical_beat_rate"], df["actual_beat"])
    _print_section("Paired Brier score: implied probability vs historical baseline", comparison)

    decomp = brier_decomposition(df["implied_prob_pre_earnings"], df["actual_beat"])
    summary = {k: v for k, v in decomp.items() if k != "bin_table"}
    _print_section("Brier decomposition for implied_prob_pre_earnings", summary)
    _print_section("Reliability diagram bin table", decomp["bin_table"])

    plot_reliability_diagram(decomp["bin_table"], FIGURES_DIR)
    print(f"\nSaved figure to {FIGURES_DIR / 'reliability_diagram.png'}")


if __name__ == "__main__":
    main()
