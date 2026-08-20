# Changelog

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
