"""Page through results and save the files.

Shows the two things that matter when you pull more than one page: let
iter_search follow the cursor, and stop on your own terms rather than draining
the whole catalogue.

    PEXAFY_API_KEY=... python download_a_set.py "vintage typewriter" 25
"""

import sys
from pathlib import Path

import httpx

from pexafy import Client, errors

query = sys.argv[1] if len(sys.argv) > 1 else "vintage typewriter"
count = int(sys.argv[2]) if len(sys.argv) > 2 else 25

out = Path("downloads")
out.mkdir(exist_ok=True)

with Client() as client, httpx.Client(timeout=60) as http:
    try:
        for photo in client.iter_search(query, max_results=count, orientation="landscape"):
            target = out / f"{photo.photo_id}.jpg"
            if target.exists():
                continue
            target.write_bytes(http.get(photo.urls.large).content)
            print(f"saved {target}  ({photo.attribution.plain})")
    except errors.RateLimitError as exc:
        print(f"quota reached, retry in {exc.retry_after or 60:.0f}s")
