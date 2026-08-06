# Polymarket public API notes (for `pull_earnings_events.py` / `pull_price_history.py`)

Read-only, unauthenticated usage only. All examples run live against production on 2026-08-06.

## 1. Gamma `/events` pagination: hard offset cap confirmed, cursor alternative exists

`GET /events` uses `offset`/`limit`, but offset pagination has a **hard cap around offset=2000**.
Confirmed by binary search on `tag_id=1013&closed=true`:

- `offset=2000` -> `200 OK`
- `offset=2001` through `offset=10000` -> `422`, body:
  `{"type":"validation error","error":"offset too large, use /events/keyset for deeper pagination"}`

This cap is not tag-specific: the same 422 appears on `closed=true&offset=5000` with no `tag_id` filter at all.
For the current earnings dataset (1,228 closed events, max offset needed ~1200) this is a non-issue. But it
means offset pagination is **not safe to rely on indefinitely** if the tag_id 1013 dataset grows past ~2000
events, or if the pipeline is ever pointed at an unfiltered/larger event set.

The fix is `GET /events/keyset` (confirmed live, returns real data): cursor-based pagination via
`after_cursor` / `next_cursor`, supports `tag_id` (array) and `closed` (bool) filters same as `/events`,
`limit` max 500 (default 20), and **explicitly rejects an `offset` param with 422** ("Not allowed... use
after_cursor instead"). Official docs:
https://docs.polymarket.com/api-reference/events/list-events-keyset-pagination

**Recommendation:** `pull_earnings_events.py` should either switch to `/events/keyset` now (future-proof,
no behavior change needed since we already paginate to exhaustion), or at minimum add a check that stops
cleanly and warns if a 422 with this message is ever received, rather than assuming an empty page means "done."

No documented max on `/markets` pagination was found beyond the generic OpenAPI `offset: integer, minimum:
0` / `limit: integer, minimum: 0` (no stated upper bound) — this project doesn't need `/markets` directly
since event objects already embed `markets[]`, so this wasn't tested further.

## 2. CLOB `/prices-history`: fixed ~15-day interval cap (fidelity-independent), no retention cutoff found

**Interval cap, not a fidelity cap.** Requesting `startTs`/`endTs` more than ~15-16 days apart fails
regardless of `fidelity`:

- 15-day window, `fidelity=60` -> `200 OK`
- 16-day window, `fidelity=60` -> `{"error":"invalid filters: 'startTs' and 'endTs' interval is too long"}`
- Same 16+ day window fails identically at `fidelity=1`, `720`, `1440`, and `10080` (i.e. coarsening the
  fidelity does NOT let you use a wider date range)

This held on both an old, low-volume token (Broadcom, closed 2025-06-05, volume ~$4.9k) and a recent,
high-volume token (NVDA, closed 2025-11-19, volume ~$995k). **Implication for `pull_price_history.py`: any
multi-month backfill must chunk requests into <=15-day windows and concatenate**, regardless of what
fidelity is requested.

**No retention cutoff found.** A 14-month-old resolved market (Broadcom) returned real, varying price data
at `fidelity=1` (minute-level) for a 1-day window near its close — 1,429 real points, not placeholders
(sample: `{"t": 1749081606, "p": 0.86}` ... `{"t": 1749167166, "p": 0.9995}`). This directly contradicts a
GitHub issue (Polymarket/py-clob-client#216) claiming resolved markets return empty below 12h granularity —
that report is most likely an artifact of the reporter's error handling silently treating the `"interval too
long"` error response as an empty array (I made the identical mistake myself mid-session and had to fix my
test script). **Conclusion: fine-grained history for old closed markets is retained and retrievable, but
only in <=15-day chunks.** No evidence of any hard retention cutoff by market age was observed in this
testing (only Broadcom at 14 months and NVDA at ~9 months were tried — a much older market, e.g. 2+ years,
was not tested and remains unconfirmed).

## 3. `outcomes` / `outcomePrices` / `clobTokenIds` ordering: confirmed consistent, Yes is always index 0

Checked Broadcom (old template) and NVDA Nov-2025 (new template) market objects directly:

```
outcomes:     ["Yes", "No"]
outcomePrices: ["1", "0"]        # Broadcom resolved Yes
clobTokenIds: ["848865...857431", "112752...901237386"]
```

`outcomes` is `["Yes","No"]` in both events checked, and maps positionally to both `outcomePrices` and
`clobTokenIds` — index 0 is always Yes. Given the sample size (2 events, both templates represented), this
looks reliable, but only 2 of 1,228 events were spot-checked here; if the pipeline wants full certainty it
should assert `outcomes == ["Yes","No"]` per event at ingestion time and raise/flag on any event that
doesn't match, rather than trusting index-0-is-Yes blindly across all 1,228+ events.

## 4. Open (`closed=false`) events for tag 1013

`GET /events?tag_id=1013&closed=false&limit=100&offset=0` currently returns **49 open events** (one partial
page; `offset=100` and beyond return 0 results, confirmed 200 OK with empty array, not an error). So there
are 49 upcoming/in-progress earnings-beat markets right now under this tag, well within the safe offset
range — no pagination concerns for the open-event query today.

## 5. Rate limits: none observed empirically

20 rapid sequential requests to both Gamma (`/events`) and CLOB (`/prices-history`) all returned `200 OK`
with no throttling, delay, or 429 seen. This matches Polymarket's informal "no rate limit (within reason)"
claim but is **not a documented guarantee** — no official numeric limit was found on docs.polymarket.com.
Treat as "seems generous for a research pipeline's request volume" rather than "confirmed unlimited."
Building in basic retry/backoff on 429/5xx is still cheap insurance and costs nothing given how few requests
this pipeline needs (~1,228 events + ~2 CLOB calls per event per 15-day chunk).

## Summary of what remains unconfirmed

- Whether `/events/keyset`'s cursor pagination has any upper bound on total pages reachable (not tested at
  scale — only confirmed it returns a valid first page and `next_cursor`).
- Whether a genuinely old (2+ year) resolved market still returns full fine-grained price history, or
  whether retention degrades past some longer horizon than the 9-14 months tested here.
- Any official numeric rate limit (only empirical negative result: no throttling in a 20-request burst).
