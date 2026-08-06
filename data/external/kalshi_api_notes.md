# Kalshi REST API notes (market data only, no auth)

Compiled 2026-08-06. All requests below were actually run against the live API with `curl`
(no API key, no auth headers). Base URL used: `https://api.elections.kalshi.com/trade-api/v2`.

## Base URL: which host to use

Kalshi has moved its API host at least twice. As of today:

- `https://trading-api.kalshi.com/trade-api/v2/...` → returns HTTP 401 with body
  `API has been moved to https://api.elections.kalshi.com/. Please check our docs on how to migrate.`
  **Do not use this host.**
- `https://api.elections.kalshi.com/trade-api/v2/...` → works, HTTP 200, no auth needed. Confirmed live.
- `https://external-api.kalshi.com/trade-api/v2/...` → also works, HTTP 200, no auth needed. Confirmed live.
  This is the host named in Kalshi's own docs pages as of 2026.

Recommendation: use `external-api.kalshi.com` as the primary base URL since it's the one the
official docs (docs.kalshi.com) reference, with `api.elections.kalshi.com` as a fallback (both
returned identical-shaped data in testing). Both are unauthenticated for the endpoints below.

No API key / auth headers were sent for any request in this doc, and every market-data endpoint
tested returned 200. The one docs page that claimed the orderbook endpoint "requires auth"
(KALSHI-ACCESS-KEY etc.) was contradicted by the live test below — it returned real data with
zero auth headers. Treat that doc claim as wrong/stale.

## Endpoint table

| Purpose | Method & path | Key params | Notes |
|---|---|---|---|
| List series (categories/products) | `GET /series?category={cat}` | `category` (e.g. `Economics`) | Returns metadata per product line, not individual contracts |
| Get one series | `GET /series/{series_ticker}` | — | |
| List markets | `GET /markets` | `series_ticker`, `event_ticker`, `tickers`, `status` (`unopened`\|`open`\|`paused`\|`closed`\|`settled`), `min_close_ts`/`max_close_ts`, `min_created_ts`/`max_created_ts`, `min_settled_ts`/`max_settled_ts`, `limit` (≤1000), `cursor` | Only reliably returns **currently live-tier** markets — see Historical vs current section |
| Get one market | `GET /markets/{ticker}` | — | Confirmed live: 200 OK, full market object |
| Order book | `GET /markets/{ticker}/orderbook?depth=N` | `depth` (0-100, 0 = all) | Confirmed live with **no auth** despite docs claiming auth is required |
| Trades | `GET /markets/trades` | `ticker`, `min_ts`/`max_ts`, `is_block_trade`, `limit`, `cursor` | |
| Candlesticks (live tier) | `GET /series/{series_ticker}/markets/{ticker}/candlesticks` | `start_ts`, `end_ts` (unix seconds, required), `period_interval` (1, 60, or 1440 minutes only), `include_latest_before_start` | 1-minute, 1-hour, 1-day resolutions only — no weekly/monthly |
| Events | `GET /events`, `GET /events/{event_ticker}` | `series_ticker`, `status` | Event = one occurrence (e.g. one FOMC meeting, one month's CPI release); groups multiple threshold markets |
| **Historical** markets | `GET /historical/markets` | `tickers`, `event_ticker`, `series_ticker`, `mve_filter`, `limit`, `cursor` | For markets archived off the live tier (see below) |
| **Historical** one market | `GET /historical/markets/{ticker}` | — | |
| **Historical** candlesticks | `GET /historical/markets/{ticker}/candlesticks` | `start_ts`, `end_ts`, `period_interval` (1/60/1440) | Same resolutions as live candlesticks |
| **Historical** trades | `GET /historical/trades` | similar to live trades | Not individually tested but documented |
| Historical/live cutoff | `GET /historical/cutoff` | — | Tells you the timestamp boundary (see below) |

### Response schema detail

**GET /markets** — each market object (fields confirmed from a live response):
```
ticker, event_ticker, market_type ("binary"|"scalar"), yes_sub_title, no_sub_title,
created_time, updated_time, open_time, close_time, latest_expiration_time (all ISO-8601 UTC,
e.g. "2026-04-28T17:55:00Z"),
status ("initialized"|"inactive"|"active"|"closed"|"determined"|"disputed"|"amended"|"finalized"),
floor_strike (number, e.g. 4.25), strike_type ("greater"|...), subtitle,
yes_bid_dollars, yes_ask_dollars, no_bid_dollars, no_ask_dollars, last_price_dollars,
previous_price_dollars, notional_value_dollars, settlement_value_dollars  — ALL prices are
DECIMAL DOLLAR STRINGS on a 0.00–1.00 scale (i.e. probability, NOT cents), e.g. "0.3000" = 30 cents = 30% implied probability,
yes_bid_size_fp, yes_ask_size_fp, volume_fp, volume_24h_fp, open_interest_fp — fixed-point
count strings, e.g. "71.47" (2 decimals; Kalshi supports fractional contract counts),
result ("yes"|"no"|"scalar"|"" if not yet settled),
rules_primary, rules_secondary (plain-text contract rules),
price_ranges: [{start, end, step}] describing the tick grid.
```
Real example (live, KXFED-27APR-T4.25, fetched today):
```json
{
  "ticker": "KXFED-27APR-T4.25",
  "event_ticker": "KXFED-27APR",
  "market_type": "binary",
  "status": "active",
  "floor_strike": 4.25,
  "strike_type": "greater",
  "yes_sub_title": "Above 4.25%",
  "yes_bid_dollars": "0.3000",
  "yes_ask_dollars": "0.3400",
  "last_price_dollars": "0.3000",
  "volume_fp": "10243.97",
  "open_interest_fp": "2049.01",
  "close_time": "2027-04-28T17:55:00Z",
  "rules_primary": "If the upper bound of the target federal funds rate published on the Federal Reserve's official website is greater than 4.25% following the Federal Reserve's Apr 28, 2027 meeting, then the market resolves to Yes."
}
```

**GET /markets/{ticker}/orderbook** — confirmed live, no auth:
```json
{"orderbook_fp":{"no_dollars":[["0.5500","9.73"],["0.5800","115.50"]],
                 "yes_dollars":[["0.1400","185.01"],["0.1500","32.18"]]}}
```
Each entry is `[price_dollars_string, quantity_fp_string]`. Only bids are shown per side
(Kalshi's binary yes/no structure makes a yes-ask equivalent to a no-bid at `1-price`, so there's
no separate "ask" array — you derive asks from the opposite side's bids).

**GET /markets/trades** — confirmed live:
```json
{"trades":[{
  "trade_id":"ee71ab13-1765-4dab-2b8e-0bcf6a1de558",
  "ticker":"KXCPI-26AUG-T1.0",
  "count_fp":"50.00",
  "yes_price_dollars":"0.0100","no_price_dollars":"0.9900",
  "taker_side":"no","taker_outcome_side":"no","taker_book_side":"ask",
  "created_time":"2026-08-05T14:31:31.825908Z",
  "is_block_trade":false
}],"cursor":""}
```
Timestamps are ISO-8601 strings (not unix ints) in trade and market objects; candlestick
endpoints use unix-second ints for `end_period_ts` and require unix-second ints for
`start_ts`/`end_ts` query params. This is an inconsistency to handle carefully in the client
(don't assume one timestamp convention project-wide).

**Candlesticks (live)** — confirmed live on a settled/historical-tier market
(`FED-23FEB-T4.50`, queried via the `/historical/markets/{ticker}/candlesticks` path since it's
past the cutoff):
```json
{
  "end_period_ts": 1672894800,
  "open_interest": "27877.50",
  "volume": "618.00",
  "price": {"open":"0.9200","high":"0.9900","low":"0.9200","close":"0.9900","mean":"0.9767","previous":"0.9700"},
  "yes_bid": {"open":"0.9400","high":"0.9700","low":"0.9200","close":"0.9700"},
  "yes_ask": {"open":"0.9900","high":"1.0000","low":"0.9900","close":"0.9900"}
}
```
All price fields dollars on 0–1 scale, `volume`/`open_interest` are fixed-point contract-count
strings. `price.*` fields can be `null` for periods with no trades (only bid/ask update).
Live (non-historical) candlestick field names use a `_dollars`/`_fp` suffix convention per the
docs page (`open_dollars`, `volume_fp`, etc.) rather than the bare names seen in the historical
response above — **the live and historical candlestick payloads have different field-naming
conventions for the same concepts.** Confirm exact live-tier field names for the market you're
querying with a one-off curl before relying on them; don't assume the historical-endpoint field
names apply to the live endpoint or vice versa.

## Historical vs current — confirmed mechanism

There are **two parallel sets of endpoints for market/candlestick data**: the plain ones
(`/markets`, `/series/{s}/markets/{m}/candlesticks`, `/markets/trades`) and a `/historical/*`
mirror (`/historical/markets`, `/historical/markets/{ticker}/candlesticks`, `/historical/trades`).
Kalshi periodically archives old settled markets out of the "live" database into a separate
historical store; once a market moves, you must use the `/historical/*` path or the plain
`/markets` endpoint returns nothing for it.

`GET /historical/cutoff` (confirmed live, no auth) returns the boundary:
```json
{"market_positions_last_updated_ts":"2026-06-07T00:00:00Z",
 "market_settled_ts":"2026-06-07T00:00:00Z",
 "orders_updated_ts":"2026-06-07T00:00:00Z",
 "trades_created_ts":"2026-06-07T00:00:00Z"}
```
Practical rule confirmed by testing: a market that settled on/before `market_settled_ts` needs
the `/historical/*` endpoints; a market that closes/settles after that cutoff is still on the
live tier and `/markets`, `/markets/trades`, and the plain candlesticks endpoint work for it.
On the day this was tested (2026-08-06) the cutoff was 2026-06-07 — i.e. roughly a 2-month
rolling window stays "live," everything older is historical-only. **Since this cutoff moves
forward over time, any pipeline pulling recent data must periodically re-check whether a given
market has crossed into the historical tier**, or just always try the live endpoint first and
fall back to `/historical/*` on an empty/404 result.

`GET /events` does NOT observe this split — event listings show up regardless of age
(confirmed: `/events?series_ticker=KXFED` returns events going back to `FED-21JUL`, a 2021
event, in the same response as 2026 events). Only the market-level and candlestick-level
endpoints are split live/historical.

**Important ticker-continuity gotcha, confirmed live:** Kalshi renamed several series tickers at
some point (dropping/adding a `KX` prefix): `FED`→`KXFED`, `CPI`→`KXCPI`, `PAYROLLS`/`PROLLS`→
`KXPAYROLLS`. These are the *same underlying series* internally — e.g. `GET /events/FED-23FEB`
returns an event object whose `series_ticker` field is `"KXFED"`, not `"FED"`. However,
`GET /historical/markets?series_ticker=KXFED` does **not** return the old `FED-*` markets (it
silently starts only from `KXFED-26APR` onward) — the `series_ticker` filter on the
markets/historical-markets endpoints appears to match the literal ticker string, not the
underlying series id, so it misses renamed history. The only way found to actually retrieve the
old markets is to enumerate event tickers first via `GET /events?series_ticker=KXFED` (which
does return the full renamed history) and then fetch each event's markets via
`GET /historical/markets?event_ticker=FED-23FEB` (confirmed this works and returns the 2023
markets). **Design implication: any ingestion script must walk series → events (not series →
markets directly) to get full history**, then pull markets per event_ticker.

## Rate limits

Kalshi's docs (`/getting_started/rate_limits`) describe tiered token-bucket limits, but they are
all framed around **authenticated** accounts (Basic/Advanced/Expert/Premier/Paragon/Prime/
Prestige tiers, 100–10,000 tokens/sec). The docs do not state a separate published number for
fully unauthenticated public reads — **this could not be confirmed**, treat unauth traffic as
subject to some default/Basic-equivalent throttling and be conservative (a modest delay between
requests, e.g. a few requests/sec, worked fine in testing here with no 429s).

Confirmed from docs and consistent with live response headers observed in this session: on a
429, the response body is `{"error": "too many requests"}` and **no `Retry-After` or
`X-RateLimit-*` headers are included** — none of the live responses captured here included any
rate-limit headers either (checked full response headers on several requests). Recommendation:
implement exponential backoff (e.g. 1s, 2s, 4s... capped at 60s) on any 429, since there's no
header to read a wait time from.

## FOMC (Fed rate decision)

- **Series ticker:** `KXFED` (title "Fed funds rate"; legacy ticker `FED` is the same underlying
  series, renamed at some point — see gotcha above).
- **Market structure:** NOT a single yes/no market and NOT explicit range-bucket markets. It's a
  **ladder of independent binary threshold markets per FOMC meeting (one event per meeting)**,
  each phrased "Will the upper bound of the federal funds rate be above X% following the Fed's
  [date] meeting?" e.g. `KXFED-27APR-T4.25`, `KXFED-27APR-T4.00`, `KXFED-27APR-T3.75`, all under
  event `KXFED-27APR`. You can back out an implied distribution over the post-meeting rate by
  looking at the price differences between adjacent thresholds, but there is no single market
  that directly quotes "rate will be exactly 4.00-4.25%." Confirmed live via
  `GET /markets?series_ticker=KXFED&status=open`.
- **Earliest observed event:** `FED-21JUL` ("Fed funds rate, July 2021 meeting"), with settled
  market `FED-21JUL-T0.25` closing 2021-07-26. Confirmed via
  `GET /historical/markets?event_ticker=FED-21JUL`. Events run essentially every FOMC meeting
  from mid-2021 through the current (2026) meetings, 46 events total under the series.

## CPI

- **Series ticker:** `KXCPI` (title "CPI"; legacy ticker `CPI` is the same underlying series).
  Note there are many adjacent-but-distinct series in the `Economics` category for related CPI
  cuts (`KXCPIYOY` "Inflation" YoY, `CPICORE`/`KXCPICORE` core CPI, `KXCPISHELTER` shelter-only,
  `KXCPIGAS` gas-only, etc.) — if the headline monthly CPI print is what's wanted, `KXCPI` is
  correct; don't accidentally pull one of the sibling series.
- **Market structure:** same ladder pattern as FOMC — a set of binary threshold markets per
  month's release, e.g. event `KXCPI-26AUG` contains `KXCPI-26AUG-T1.0`, `KXCPI-26AUG-T0.9`,
  `KXCPI-26AUG-T0.8`, etc., each phrased "Will CPI rise more than X% in [month] [year]?" Not a
  single binary market, not explicitly labeled ranges — same threshold-ladder shape as FOMC.
  Confirmed live via `GET /markets?series_ticker=KXCPI&status=open`.
- **Earliest observed event:** `CPI-21JUN` ("CPI in June 2021"), settled market
  `CPI-21JUN-T0.6` closing 2021-07-12. Confirmed via
  `GET /historical/markets?event_ticker=CPI-21JUN`. 61 monthly events total, essentially every
  month from mid-2021 through mid-2026.

## Jobs report (nonfarm payrolls / NFP)

- **Series ticker:** `KXPAYROLLS` (title "Jobs numbers"; legacy tickers `PAYROLLS` and `PROLLS`
  are the same underlying series across different renaming periods).
- **Market structure:** same threshold-ladder pattern, e.g. event `KXPAYROLLS-26NOV` contains
  `KXPAYROLLS-26NOV-T90000`, `KXPAYROLLS-26NOV-T80000`, `KXPAYROLLS-26NOV-T70000`, phrased "Will
  above X jobs be added in [month] [year]?" Confirmed live via
  `GET /markets?series_ticker=KXPAYROLLS&status=open`.
- **Earliest observed event:** `PROLLS-23MAR` ("Jobs numbers in Mar 2023"), settled market
  `PROLLS-23MAR-T500000` closing 2023-04-07. Confirmed via
  `GET /historical/markets?event_ticker=PROLLS-23MAR`. **This is notably shorter history than
  FOMC/CPI** — only back to March 2023, not 2021 — 45 monthly events total. There is no earlier
  jobs-report event under this series; checked exhaustively (full unpaginated event list has 45
  entries, none earlier than `PROLLS-23MAR`).

## Open questions / things NOT confirmed

- Exact unauthenticated rate limit ceiling (requests/sec) is not published anywhere found; only
  authenticated tiers are documented. Be conservative.
- The `/historical/trades`, `/historical/orders`, `/historical/fills`, `/historical/positions`
  endpoints were found in the docs index but not individually tested live (the last three are
  portfolio/authenticated-only anyway and out of scope for this project).
- Live-tier candlestick field naming (`open_dollars` vs bare `open`) could not be double-checked
  against a real non-empty live-tier response in this session — the one live-tier candlestick
  query attempted (`KXFED-27APR-T4.25`, 1-day interval) returned an empty `candlesticks: []`
  array (likely just too little trading activity in the queried window), so the exact field
  names for a populated live (non-archived) candlestick response are inferred from docs only,
  not verified against real data. The historical-endpoint field names (bare `open`/`close`/etc.,
  shown above) ARE verified against real data.
- Whether `min_close_ts`/`max_close_ts`/etc. filters work at all on `/historical/markets` is
  unconfirmed — they appeared to be silently ignored in testing (results didn't change when a
  narrow `max_close_ts` was added). Documented params for that endpoint are only `tickers`,
  `event_ticker`, `series_ticker`, `mve_filter`, `limit`, `cursor` — treat the ts filters as
  live-endpoint-only.
