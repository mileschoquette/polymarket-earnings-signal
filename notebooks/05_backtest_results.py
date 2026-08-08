"""Driver for the backtest stage: builds the divergence signal (no look-ahead expanding-std
threshold), runs the volatility-targeted backtest at both exit horizons, reports performance
metrics, and saves an equity-curve comparison.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from src.strategy.backtest import run_backtest
from src.strategy.benchmarks import (
    buy_and_hold_direction,
    historical_only_direction,
    perfect_foresight_direction,
)
from src.strategy.performance import (
    aggregate_by_date,
    annualized_sharpe,
    calmar_ratio,
    dates_per_year,
    hit_rate,
    max_drawdown,
    sortino_ratio,
)
from src.strategy.signal import compute_signal
from src.strategy.significance import block_bootstrap_sharpe_ci, jobson_korkie_test, permutation_test

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "earnings_panel.parquet"
SPY_PATH = Path(__file__).resolve().parents[1] / "data" / "raw" / "yfinance" / "SPY.parquet"
FIGURES_DIR = Path(__file__).resolve().parents[1] / "paper" / "figures"
BLUE = "#2a78d6"  # categorical slot 1, validated in dataviz palette (t+1)
ORANGE = "#eb6834"  # categorical slot 2, validated in dataviz palette (t+5)
GRAY = "#52514e"  # muted reference-line ink, validated in dataviz palette

HORIZONS = {"t_plus_1": BLUE, "t_plus_5": ORANGE}


def _events_per_year(df):
    dates = pd.to_datetime(df["scheduled_date"])
    span_years = (dates.max() - dates.min()).days / 365.25
    return len(df) / span_years


def plot_equity_curves(results_by_horizon, out_dir):
    """Cumulative sum of net_pnl over time, one line per exit horizon."""
    fig, ax = plt.subplots(figsize=(9, 6))
    for horizon, color in HORIZONS.items():
        result = results_by_horizon[horizon].sort_values("scheduled_date")
        dates = pd.to_datetime(result["scheduled_date"])
        equity = result["net_pnl"].cumsum()
        ax.plot(dates, equity, color=color, linewidth=2, label=horizon.replace("_", " "))
    ax.axhline(0, color=GRAY, linewidth=0.75, alpha=0.5)
    ax.set_xlabel("Scheduled date")
    ax.set_ylabel("Cumulative net P&L (sum of risk-scaled per-event returns)")
    ax.set_title("Divergence signal backtest: equity curve by exit horizon")
    ax.legend(frameon=False, loc="best")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(out_dir / "backtest_equity_curve.png", dpi=150)
    plt.close(fig)


def plot_strategy_vs_market(daily_pnl, out_dir, horizon_label):
    """Strategy cumulative net P&L (date-aggregated, risk-scaled units) against SPY's passive
    cumulative return over the identical calendar window, so the reader can see the strategy's
    path next to simply holding the market over the same period. The two lines aren't in
    dimensionally identical units (the strategy's is a sum of vol-targeted per-event risk
    contributions, not a % return on fully-deployed capital), so this is a shape/timing
    comparison, not a literal dollar-for-dollar return comparison -- noted here rather than
    implied by the chart alone.
    """
    spy_close = pd.read_parquet(SPY_PATH)["Close"]
    spy_close.index = spy_close.index.tz_localize(None)

    start, end = daily_pnl.index.min(), daily_pnl.index.max()
    spy_window = spy_close[(spy_close.index >= start) & (spy_close.index <= end)]
    spy_cum_return = spy_window / spy_window.iloc[0] - 1
    strategy_cum_pnl = daily_pnl.cumsum()

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.plot(strategy_cum_pnl.index, strategy_cum_pnl.values, color=BLUE, linewidth=2,
            label=f"Divergence strategy ({horizon_label}, cumulative net P&L)")
    ax.plot(spy_cum_return.index, spy_cum_return.values, color=GRAY, linewidth=2, linestyle="--",
            label="SPY (buy-and-hold, cumulative return)")
    ax.axhline(0, color=GRAY, linewidth=0.75, alpha=0.5)
    ax.set_xlabel("Date")
    ax.set_ylabel("Cumulative return / P&L")
    ax.set_title("Strategy vs. market: cumulative return over time")
    ax.legend(frameon=False, loc="best")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(out_dir / "strategy_vs_market.png", dpi=150)
    plt.close(fig)


def _summarize_strategy(name, result, events_per_year):
    """One row of the benchmark comparison table: Sharpe (event-level, date-aggregated),
    executed trades, and hit rate.
    """
    pnl, executed = result["net_pnl"], result["position_size"] > 0
    daily_pnl = aggregate_by_date(pnl, result["scheduled_date"])
    daily_events_per_year = dates_per_year(result["scheduled_date"])
    return {
        "strategy": name,
        "sharpe_event": annualized_sharpe(pnl, events_per_year),
        "sharpe_date": annualized_sharpe(daily_pnl, daily_events_per_year),
        "executed_trades": int(executed.sum()),
        "hit_rate": hit_rate(pnl, executed) if executed.any() else float("nan"),
    }


def run_benchmarks_and_significance(df, horizon="t_plus_1"):
    """Benchmarks the main divergence signal against buy-and-hold (isolates whether long/short/
    flat selection beats always-long), historical-only (isolates whether firm history alone,
    without the market's price, would already look profitable), and a perfect-foresight ceiling
    (not a real competitor -- uses the realized outcome), all run through the identical
    run_backtest machinery as the main strategy. Then reports a permutation test (does the
    observed Sharpe beat random direction assignment over the same trades?) and a block-bootstrap
    Sharpe CI clustered by scheduled_date (respecting same-day event clustering).
    """
    signal_df = compute_signal(df)
    events_per_year = _events_per_year(signal_df)

    rows = [
        _summarize_strategy("main (divergence signal)", run_backtest(signal_df, exit_horizon=horizon), events_per_year),
        _summarize_strategy("buy-and-hold", run_backtest(buy_and_hold_direction(df), exit_horizon=horizon), events_per_year),
        _summarize_strategy("historical-only", run_backtest(historical_only_direction(df), exit_horizon=horizon), events_per_year),
        _summarize_strategy(
            "perfect foresight (CEILING, not a competitor)",
            run_backtest(perfect_foresight_direction(df), exit_horizon=horizon),
            events_per_year,
        ),
    ]
    table = pd.DataFrame(rows).set_index("strategy")

    print(f"\n=== Benchmarks and significance ({horizon}) ===")
    print(table.to_string(float_format=lambda x: f"{x:.3f}"))

    print("\n--- Permutation test: main signal vs. random direction assignment over the same trades ---")
    perm = permutation_test(signal_df, "direction", horizon, n_permutations=1000, seed=0)
    print(f"observed Sharpe (date-aggregated): {perm['observed_sharpe']:.3f}")
    print(f"null Sharpe mean / std:            {perm['null_sharpes'].mean():.3f} / {perm['null_sharpes'].std(ddof=1):.3f}")
    print(f"p-value (one-sided, P(null >= observed)): {perm['p_value']:.4f}")

    print("\n--- Block bootstrap 90% CI for main signal's Sharpe (clustered by scheduled_date) ---")
    boot = block_bootstrap_sharpe_ci(signal_df, "direction", horizon, n_boot=1000, seed=0, ci=0.90)
    print(f"observed Sharpe (date-aggregated): {boot['observed_sharpe']:.3f}")
    print(f"90% CI: [{boot['lo']:.3f}, {boot['hi']:.3f}]")

    print("\n--- Jobson-Korkie test: main signal vs. buy-and-hold (date-aggregated net_pnl) ---")
    main_daily = aggregate_by_date(
        run_backtest(signal_df, exit_horizon=horizon)["net_pnl"], signal_df["scheduled_date"],
    )
    bh_result = run_backtest(buy_and_hold_direction(df), exit_horizon=horizon)
    bh_daily = aggregate_by_date(bh_result["net_pnl"], bh_result["scheduled_date"])
    jk = jobson_korkie_test(main_daily, bh_daily)
    print(f"sharpe_a (main, per-period): {jk['sharpe_a']:.4f}, sharpe_b (buy-and-hold, per-period): {jk['sharpe_b']:.4f}")
    print(f"z-statistic: {jk['z_stat']:.3f}, p-value: {jk['p_value']:.4f}, n: {jk['n']}")

    return table, perm, boot, jk


def main():
    df = pd.read_parquet(DATA_PATH)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    signal_df = compute_signal(df)
    events_per_year = _events_per_year(signal_df)
    n_non_flat = int((signal_df["direction"] != 0).sum())
    print(f"events_per_year: {events_per_year:.2f}")
    print(f"non-flat (direction != 0) events: {n_non_flat}/{len(signal_df)}")

    results_by_horizon = {}
    for horizon in HORIZONS:
        result = run_backtest(signal_df, exit_horizon=horizon)
        results_by_horizon[horizon] = result

        pnl, executed = result["net_pnl"], result["position_size"] > 0
        print(f"\n--- {horizon} (event-level, upper bound -- see date-aggregated below) ---")
        print(f"executed trades: {int(executed.sum())} (non-flat signal: {int((result['direction'] != 0).sum())})")
        print(f"annualized Sharpe: {annualized_sharpe(pnl, events_per_year):.3f}")
        print(f"Sortino ratio:     {sortino_ratio(pnl, events_per_year):.3f}")
        print(f"max drawdown:      {max_drawdown(pnl):.4f}")
        print(f"hit rate:          {hit_rate(pnl, executed):.3f}")
        print(f"Calmar ratio:      {calmar_ratio(pnl, events_per_year):.3f}")

        daily_pnl = aggregate_by_date(pnl, result["scheduled_date"])
        daily_events_per_year = dates_per_year(result["scheduled_date"])
        print(f"\n--- {horizon} (date-aggregated, same-day events summed into one period) ---")
        print(f"distinct trading dates: {len(daily_pnl)} (dates_per_year: {daily_events_per_year:.2f})")
        print(f"annualized Sharpe: {annualized_sharpe(daily_pnl, daily_events_per_year):.3f}")
        print(f"Sortino ratio:     {sortino_ratio(daily_pnl, daily_events_per_year):.3f}")
        print(f"max drawdown:      {max_drawdown(daily_pnl):.4f}")
        print(f"Calmar ratio:      {calmar_ratio(daily_pnl, daily_events_per_year):.3f}")

        if horizon == "t_plus_1":
            plot_strategy_vs_market(daily_pnl, FIGURES_DIR, horizon.replace("_", " "))

    plot_equity_curves(results_by_horizon, FIGURES_DIR)
    print(f"\nSaved figure to {FIGURES_DIR / 'backtest_equity_curve.png'}")
    print(f"Saved figure to {FIGURES_DIR / 'strategy_vs_market.png'}")

    for horizon in HORIZONS:
        run_benchmarks_and_significance(df, horizon=horizon)

    print("\n=== Transaction-cost sensitivity (main signal, t_plus_1, date-aggregated Sharpe) ===")
    for cost_bps in (5, 10, 20):
        cost_result = run_backtest(signal_df, exit_horizon="t_plus_1", cost_bps=cost_bps)
        cost_daily = aggregate_by_date(cost_result["net_pnl"], cost_result["scheduled_date"])
        cost_sharpe = annualized_sharpe(cost_daily, dates_per_year(cost_result["scheduled_date"]))
        print(f"cost_bps={cost_bps:>2}: annualized Sharpe = {cost_sharpe:.3f}")


if __name__ == "__main__":
    main()
