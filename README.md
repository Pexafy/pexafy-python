# pexafy-python

Python client for the [Pexafy](https://pexafy.com) image search API. Search a
catalogue of free stock photos by describing what you want, or by handing it an
image to match.

```bash
pip install pexafy
```

## Getting started

```python
from pexafy import Client

client = Client("your-api-key")

for photo in client.search("a quiet street in the rain", per_page=5):
    print(photo.urls.regular, "-", photo.alt_text)
```

The key comes from your [dashboard](https://pexafy.com/dashboard/); the free
tier does not ask for a card. If you would rather not put it in the code, the
client picks up `PEXAFY_API_KEY` from the environment.

## Writing queries

Search runs on meaning, not keywords, so full sentences work better than a pile
of nouns. `two people hiking on a ridge at dawn` finds what you would expect;
`hiking dawn people` gives you a worse ranking, because you have thrown away
the relationships between the words.

Filters narrow the result set after the semantic match:

```python
result = client.search(
    "an empty office at night",
    orientation="landscape",
    color_name="blue",
    source=["Pexels", "Unsplash"],
    per_page=20,
)

print(len(result), "photos in", result.took_ms, "ms")
```

`orientation`, `source` and `license_type` take several values, as a list or as a comma
separated string. `color_name` takes one: the API filters on a single colour, and passing
more raises rather than quietly filtering on whichever one arrived last.

## Paging

A single call returns one page. `iter_search` follows the cursor for you and
yields photos until the results run out or you have seen enough:

```python
for photo in client.iter_search("vintage typewriter", max_results=200):
    download(photo.urls.large)
```

## Search by image

Pass a path, raw bytes, or an open file:

```python
similar = client.search_by_image("moodboard/reference.jpg", per_page=12)
```

If you already have a photo id, `client.similar(photo_id)` is cheaper — the
image does not have to be uploaded and encoded again.

## Async

The same surface, awaitable:

```python
import asyncio
from pexafy import AsyncClient

async def main():
    async with AsyncClient() as client:
        pages = await asyncio.gather(
            client.search("desert road"),
            client.search("snow covered pines"),
        )
    for page in pages:
        print(len(page))

asyncio.run(main())
```

## Errors

Everything raised inherits from `PexafyError`. The ones worth catching
separately:

```python
from pexafy import errors

try:
    client.search("...")
except errors.RateLimitError as exc:
    time.sleep(exc.retry_after or 60)
except errors.AuthenticationError:
    ...          # key is missing, malformed or revoked
except errors.APIError as exc:
    print(exc.status_code, exc.code, exc.request_id)
```

`request_id` is worth logging. It is the fastest way to get an answer if you
need to ask about a specific call.

Timeouts and 5xx responses are retried twice with backoff, and `Retry-After` is
honoured when the server sends it. Set `max_retries=0` if you would rather
handle that yourself.

## Command line

```
$ pexafy search "morning fog over pine trees" -n 3
0.847  019e0eb8-b028-73cb-9296-dfa70f557bc9   4000x2667   green      Pexels     https://...
0.812  019e4c9b-3022-7660-b43d-e730b8435f24   6000x4000   green      Unsplash   https://...
0.798  019e4f39-66d4-7ef2-bc9b-eb5340fd243e   3648x5472   grey       Pexels     https://...
```

`pexafy photo <id>`, `pexafy similar <id>` and `pexafy usage` are also there.
Add `--json` to any of them for the raw response.

## Attribution

Photos come from several providers with different licence terms. Every photo
carries an `attribution` object with a ready made credit line:

```python
photo.attribution.plain   # Photo by J. Doe
photo.attribution.html    # <a href="...">J. Doe</a>
```

Check `photo.license_type` if your use depends on it.

## Reference

| Method | What it does |
| --- | --- |
| `search(q, **filters)` | one page of results |
| `iter_search(q, max_results=None, **filters)` | every page, cursor handled |
| `search_by_image(image, **filters)` | match an image you supply |
| `get_photo(photo_id)` | one photo by id |
| `similar(photo_id, **filters)` | photos close to an existing one |
| `colors()` `sources()` `orientations()` `licenses()` | filter values you can use |
| `suggest_photographers(q)` `photographer(username)` | photographer lookup |
| `collections()` `create_collection(name)` `add_to_collection(id, photo_id)` | saved sets |
| `usage()` `usage_daily()` `usage_monthly()` `usage_by_key()` | where you are against your quota |

Full API documentation is at [docs.pexafy.com](https://docs.pexafy.com).

## Requirements

Python 3.9 or newer. The only dependency is `httpx`.

## Licence

MIT.
