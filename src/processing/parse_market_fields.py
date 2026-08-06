"""Extract ticker/basis/scheduled-date/consensus-EPS from a Polymarket earnings-tag market.

Parses from `description` text rather than `slug`, because the slug's date/value encoding is
inconsistent across events (MM-DD-YYYY vs YYYY-MM-DD, zero-padded vs not, "1pt5" vs "1" with no
decimal, occasional trailing disambiguator suffixes), while the auto-generated description prose
follows one of a few stable sentence templates regardless of slug quirks. Events that don't match
any known template (e.g. a handful of unrelated non-earnings markets that share the "Earnings" tag)
return None and should be dropped, not guessed at.
"""
import re

_TITLE_TICKER_RE = re.compile(r"\(([A-Z]{1,6}(?:\.[A-Z])?)\)\s*beat")
_DESC_TICKER_RE = re.compile(r"\((?:NASDAQ|NYSE|NYSEAMERICAN|NYSEARCA|OTC|OTCMKTS):\s*([A-Z.]{1,6})\)")
_DATE_RE = re.compile(r"release\b.{0,30}?earnings on ([A-Za-z]+ \d{1,2}, \d{4}|\d{4}-\d{2}-\d{2})")
_CONSENSUS_RE = re.compile(r"estimate for.*?is (-?\$-?\d+(?:\.\d+)?)", re.DOTALL)
_NON_GAAP_RE = re.compile(r"non-GAAP", re.IGNORECASE)
_GAAP_RE = re.compile(r"(?<!non-)GAAP", re.IGNORECASE)

def _parse_ticker(title, description):
    m = _TITLE_TICKER_RE.search(title) or _DESC_TICKER_RE.search(description)
    return m.group(1) if m else None


def _parse_scheduled_date(description):
    from datetime import datetime

    m = _DATE_RE.search(description)
    if not m:
        return None
    raw = m.group(1)
    fmt = "%Y-%m-%d" if raw[:4].isdigit() and "-" in raw[:5] else "%B %d, %Y"
    try:
        return datetime.strptime(raw, fmt).date().isoformat()
    except ValueError:
        return None


def _parse_consensus_eps(description):
    m = _CONSENSUS_RE.search(description)
    if not m:
        return None
    raw = m.group(1).replace("$", "")
    try:
        return float(raw)
    except ValueError:
        return None


def _parse_basis(description):
    if _NON_GAAP_RE.search(description):
        return "non-GAAP"
    if _GAAP_RE.search(description):
        return "GAAP"
    return None


def parse_market(event):
    """Extract {ticker, basis, scheduled_date, consensus_eps} from one event's primary market. None if any field can't be confidently parsed."""
    markets = event.get("markets") or []
    if not markets:
        return None
    market = markets[0]
    title = event.get("title", "")
    description = market.get("description") or ""

    ticker = _parse_ticker(title, description)
    scheduled_date = _parse_scheduled_date(description)
    consensus_eps = _parse_consensus_eps(description)
    basis = _parse_basis(description)

    if not all([ticker, scheduled_date, consensus_eps is not None, basis]):
        return None

    return {
        "event_id": event.get("id"),
        "slug": market.get("slug"),
        "ticker": ticker,
        "basis": basis,
        "scheduled_date": scheduled_date,
        "consensus_eps": consensus_eps,
    }
