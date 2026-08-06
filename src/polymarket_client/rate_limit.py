import time


def request_with_backoff(fn, max_retries=5, base_delay=1.0):
    """Call fn() (a zero-arg request), retrying with exponential backoff on HTTP 429 or 5xx."""
    resp = fn()
    for attempt in range(max_retries):
        if resp.status_code < 429:
            return resp
        time.sleep(min(base_delay * 2**attempt, 60))
        resp = fn()
    return resp
