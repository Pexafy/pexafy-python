# Changelog

## 1.0.0

The client covers every public endpoint of the API, with both clients alike,
and its methods are now stable: within 1.x, an upgrade does not break code
written against 1.0.

- `AsyncClient` gains the methods only `Client` had: photographer lookup
  (`suggest_photographers`, `photographer`), collections (`collections`,
  `create_collection`, `collection`, `delete_collection`, `add_to_collection`,
  `remove_from_collection`) and usage history (`usage_daily`, `usage_monthly`,
  `usage_by_key`). A test now fails if the two clients drift apart again.
- `get_photo(photo_id, fields=...)` selects the fields returned, like `search`.
- `usage_daily(days=...)` and `usage_monthly(months=...)` set the history
  window (up to 90 days and 24 months; the API defaults to 30 and 12).
- Classified "Production/Stable" on PyPI.

## 0.1.2

- A 429 is retried only when it is the per-minute rate limit (`RATE_LIMITED`).
  An exhausted daily or monthly quota (`DAILY_QUOTA_EXCEEDED`,
  `QUOTA_EXCEEDED`) now raises `RateLimitError` at once: the daily one used to
  be retried with a 60-second wait each time, stalling the caller for two
  minutes before failing anyway.
- `pexafy.__version__` (and the `user-agent` it builds) said 0.1.0 in the 0.1.1
  release; it now matches the package version.

## 0.1.1

Fixed multi-valued filters, which never worked against the live API.

- `orientation`, `source` and `license_type` now go out as repeated query
  parameters. They were sent comma separated, which the server reads as one
  value: `source` and `license_type` matched nothing and returned an empty
  page, while an unrecognised `orientation` was dropped and the caller got an
  unfiltered page back with no indication anything had been ignored.
- `color_name` refuses several values instead of joining them. The API filters
  on the last one it receives, so the old behaviour returned a result set built
  from a filter the caller had not asked for.

## 0.1.0

First release.

- Synchronous and asynchronous clients
- Text search, image search, similar photos, facets, collections, usage
- Cursor paging handled by `iter_search`
- Typed exceptions, retries on timeouts and 5xx, `Retry-After` honoured
- `pexafy` command line client
