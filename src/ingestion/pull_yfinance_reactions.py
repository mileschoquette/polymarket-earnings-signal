"""Pull per-ticker daily OHLCV history and sector/market-cap metadata from yfinance.

One history pull per unique ticker (not per quarter): many tickers report multiple quarters in
the earnings-tag dataset, so we span each ticker's full earliest-to-latest scheduled_date range
in a single call, padded on each side for pre/post-earnings return windows.
"""
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

import yfinance as yf

from src.processing.parse_market_fields import parse_market

EVENTS_DIR = Path(__file__).resolve().parents[2] / "data" / "raw" / "polymarket" / "events"
OUT_DIR = Path(__file__).resolve().parents[2] / "data" / "raw" / "yfinance"
PAD_DAYS = 10


def _collect_ticker_date_ranges():
    """{ticker: (earliest_scheduled_date, latest_scheduled_date)} across all parsed events."""
    ranges = {}
    for path in EVENTS_DIR.glob("*.json"):
        event = json.loads(path.read_text())
        parsed = parse_market(event)
        if parsed is None:
            continue
        ticker = parsed["ticker"]
        date = datetime.strptime(parsed["scheduled_date"], "%Y-%m-%d").date()
        lo, hi = ranges.get(ticker, (date, date))
        ranges[ticker] = (min(lo, date), max(hi, date))
    return ranges


def _yf_symbol(ticker):
    """Yahoo Finance uses hyphens for share classes (BRK.A -> BRK-A), not dots."""
    return ticker.replace(".", "-")


def _fetch_history(ticker, start, end):
    hist = yf.Ticker(_yf_symbol(ticker)).history(
        start=start.isoformat(), end=end.isoformat(), interval="1d", auto_adjust=False
    )
    return None if hist.empty else hist


def _fetch_meta(ticker):
    """sector/industry/marketCap, or None for any field yfinance's flaky .info omits."""
    try:
        info = yf.Ticker(_yf_symbol(ticker)).info
    except Exception:
        info = {}
    return {
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "marketCap": info.get("marketCap"),
    }


def pull_ticker(ticker, lo, hi):
    """Fetch and cache one ticker's history + metadata. Returns True on success (history found)."""
    price_path = OUT_DIR / f"{ticker}.parquet"
    meta_path = OUT_DIR / f"{ticker}_meta.json"
    if price_path.exists() and meta_path.exists():
        return True

    start = lo - timedelta(days=PAD_DAYS)
    end = hi + timedelta(days=PAD_DAYS)
    hist = _fetch_history(ticker, start, end)
    if hist is None:
        return False

    hist.to_parquet(price_path)
    meta_path.write_text(json.dumps(_fetch_meta(ticker), indent=2))
    return True


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    ranges = _collect_ticker_date_ranges()
    tickers = sorted(ranges)
    print(f"unique tickers: {len(tickers)}")

    failed = []
    for i, ticker in enumerate(tickers, start=1):
        lo, hi = ranges[ticker]
        try:
            ok = pull_ticker(ticker, lo, hi)
        except Exception as e:
            print(f"  [{ticker}] unexpected error: {e}")
            ok = False
        if not ok:
            failed.append(ticker)
        if i % 50 == 0:
            print(f"progress: {i}/{len(tickers)} tickers processed, {len(failed)} failed so far")
        time.sleep(0.2)

    n_ok = len(tickers) - len(failed)
    print(f"done: {n_ok}/{len(tickers)} succeeded, {len(failed)} failed")
    if failed:
        print(f"failed tickers ({len(failed)}): {failed}")


if __name__ == "__main__":
    main()
