"""Driver for the descriptive-analysis stage: prints coverage, distribution, beat-rate, and
liquidity-proxy summaries, and saves figures to paper/figures/.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from src.analysis.descriptive_stats import (
    beat_rate_by_sector,
    eps_and_prob_summary,
    historical_beat_rate_summary,
    liquidity_by_quarter,
    realized_beat_rate_overall,
    sample_coverage_by_quarter,
)

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "earnings_panel.parquet"
FIGURES_DIR = Path(__file__).resolve().parents[1] / "paper" / "figures"
BLUE = "#2a78d6"  # single-series categorical slot 1, validated in dataviz palette


def _print_section(title, obj):
    print(f"\n{'=' * len(title)}\n{title}\n{'=' * len(title)}")
    print(obj)


def plot_events_per_quarter(coverage, out_dir):
    """Bar chart of event count per quarter. Deliberately does not annotate unique-ticker counts
    on the bars: that figure is close to but not identical to the event count (a small number of
    tickers report more than once within the same quarter), and an earlier version of this chart
    that overlaid both numbers on the same bar read as an error to reviewers. The unique-ticker
    breakdown, when needed, is reported in prose instead.
    """
    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = coverage.index.astype(str)
    ax.bar(x, coverage["n_events"], color=BLUE, width=0.6)
    for i, n_events in enumerate(coverage["n_events"]):
        ax.text(i, n_events + 3, str(n_events), ha="center", fontsize=8, color="#52514e")
    ax.set_title("Polymarket earnings-beat events per quarter")
    ax.set_ylabel("Number of events")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(out_dir / "events_per_quarter.png", dpi=150)
    plt.close(fig)


def plot_beat_rate_by_sector(sector_rates, out_dir):
    """Horizontal bar chart of beat rate by sector, with n shown next to each bar."""
    fig, ax = plt.subplots(figsize=(8, 5))
    y = range(len(sector_rates))
    ax.barh(y, sector_rates["beat_rate"], color=BLUE, height=0.6)
    ax.set_yticks(list(y))
    ax.set_yticklabels([f"{s} (n={n})" for s, n in zip(sector_rates.index, sector_rates["n_events"])])
    ax.invert_yaxis()
    ax.set_xlabel("Realized beat rate")
    ax.set_title("Realized earnings-beat rate by sector")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(out_dir / "beat_rate_by_sector.png", dpi=150)
    plt.close(fig)


def plot_liquidity_trend(liquidity, out_dir):
    """Line chart of mean price-history points per event by quarter (data-density/liquidity proxy)."""
    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = liquidity.index.astype(str)
    ax.plot(x, liquidity["mean"], color=BLUE, marker="o", linewidth=2)
    ax.set_title("Price-history data density per event, by quarter")
    ax.set_ylabel("Mean price points per event")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(out_dir / "liquidity_proxy_trend.png", dpi=150)
    plt.close(fig)


def main():
    df = pd.read_parquet(DATA_PATH)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    coverage = sample_coverage_by_quarter(df)
    _print_section("Sample coverage by quarter", coverage)

    _print_section("Consensus EPS / implied-probability distributions", eps_and_prob_summary(df))

    overall_rate = realized_beat_rate_overall(df)
    sector_rates = beat_rate_by_sector(df)
    _print_section("Overall realized beat rate", f"{overall_rate:.3f} (n={len(df)})")
    _print_section("Realized beat rate by sector", sector_rates)

    liquidity = liquidity_by_quarter(df)
    _print_section("Price-history point count by quarter (liquidity/data-density proxy)", liquidity)

    _print_section("Historical beat-rate baseline distribution", historical_beat_rate_summary(df))

    plot_events_per_quarter(coverage, FIGURES_DIR)
    plot_beat_rate_by_sector(sector_rates, FIGURES_DIR)
    plot_liquidity_trend(liquidity, FIGURES_DIR)
    print(f"\nSaved figures to {FIGURES_DIR}")


if __name__ == "__main__":
    main()
