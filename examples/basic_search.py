"""The smallest useful thing: search and print what came back.

    PEXAFY_API_KEY=... python basic_search.py "a quiet street in the rain"
"""

import sys

from pexafy import Client

query = sys.argv[1] if len(sys.argv) > 1 else "a quiet street in the rain"

with Client() as client:
    result = client.search(query, per_page=5)
    print(f"{len(result)} photos in {result.took_ms:.0f} ms\n")
    for photo in result:
        print(f"{photo.relevance_score:.3f}  {photo.alt_text}")
        print(f"        {photo.urls.regular}")
        print(f"        {photo.attribution.plain}\n")
