from src.processing.parse_market_fields import parse_market


def _event(title, description, slug="whatever"):
    return {"id": "1", "title": title, "markets": [{"slug": slug, "description": description}]}


def test_parses_standard_template():
    event = _event(
        "Will NVIDIA (NVDA) beat quarterly earnings?",
        "As of market creation, NVIDIA is estimated to release earnings on November 19, 2025. "
        "The Street consensus estimate for NVIDIA's non-GAAP EPS for the relevant quarter is $1.25 "
        "as of market creation. This market will resolve to \"Yes\" if...",
    )
    result = parse_market(event)
    assert result == {
        "event_id": "1",
        "slug": "whatever",
        "ticker": "NVDA",
        "basis": "non-GAAP",
        "scheduled_date": "2025-11-19",
        "consensus_eps": 1.25,
    }


def test_parses_negative_consensus_with_leading_sign():
    event = _event(
        "Will Warner Bros. Discovery (WBD) beat quarterly earnings?",
        "Warner Bros. Discovery is estimated to release earnings on November 6, 2025. The Street "
        "consensus estimate for Warner Bros. Discovery's GAAP EPS for the relevant quarter is $-0.08. "
        "This market will resolve...",
    )
    result = parse_market(event)
    assert result["consensus_eps"] == -0.08
    assert result["basis"] == "GAAP"


def test_parses_negative_consensus_with_leading_dollar():
    event = _event(
        "Will Applied Digital (APLD) beat quarterly earnings?",
        "Applied Digital Corporation is estimated to release earnings on October 9, 2025. The Street "
        "consensus estimate for Applied Digital Corporation's non-GAAP EPS for the relevant quarter is "
        "-$0.16. This market will resolve...",
    )
    result = parse_market(event)
    assert result["consensus_eps"] == -0.16


def test_parses_company_name_with_periods_without_breaking_consensus_regex():
    event = _event(
        "Will AZZ (AZZ) beat quarterly earnings?",
        "AZZ Inc. is estimated to release earnings on October 8, 2025. The Street consensus estimate "
        "for AZZ Inc.'s non-GAAP EPS for the relevant quarter is $1.57. This market will resolve...",
    )
    result = parse_market(event)
    assert result["consensus_eps"] == 1.57
    assert result["ticker"] == "AZZ"


def test_parses_iso_date_secondary_template():
    event = _event(
        "Will MillerKnoll (MLKN) beat its quarterly EPS estimate?",
        "MillerKnoll Inc is scheduled to release earnings on 2025-09-23. The Bloomberg consensus "
        "estimate for MillerKnoll Inc's non-GAAP EPS for the relevant quarter is $0.34.",
    )
    result = parse_market(event)
    assert result["scheduled_date"] == "2025-09-23"
    assert result["consensus_eps"] == 0.34


def test_parses_oldest_template_ticker_from_description_exchange_mention():
    event = _event(
        "Will Broadcom beat Q2 earnings forecast ($1.57 EPS)?",
        "Broadcom is scheduled to release 2025 Q2 earnings on June 5, 2025. The consensus estimate "
        "for Broadcom’s non-GAAP diluted earnings per share is $1.57. This market will resolve to "
        "“Yes” if the non-GAAP diluted earnings per share (adjusted EPS) reported by Broadcom "
        "Inc. (NASDAQ: AVGO) for the second quarter of its fiscal year 2025, is greater than $1.57.",
    )
    result = parse_market(event)
    assert result["ticker"] == "AVGO"
    assert result["scheduled_date"] == "2025-06-05"
    assert result["consensus_eps"] == 1.57


def test_returns_none_for_unrelated_non_earnings_market():
    event = _event(
        "How much $ did MrBeast’s Twitter post with 124m views make?",
        "On Jan 19 MrBeast posted the following on X asking people to guess how much revenue his "
        "tweet with over 124m views made. This market will resolve to \"Yes\" if...",
    )
    assert parse_market(event) is None


def test_returns_none_when_no_markets():
    assert parse_market({"id": "1", "title": "x", "markets": []}) is None
