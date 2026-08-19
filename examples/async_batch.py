"""Run several searches at once.

Filling one page per section of a document is the common case, and there is no
reason to do it serially.

    PEXAFY_API_KEY=... python async_batch.py
"""

import asyncio

from pexafy import AsyncClient

SECTIONS = [
    "an empty office at night",
    "hands typing on a mechanical keyboard",
    "a server room seen from the doorway",
    "someone reading on a train",
]


async def main():
    async with AsyncClient() as client:
        pages = await asyncio.gather(*(client.search(q, per_page=3) for q in SECTIONS))

    for query, page in zip(SECTIONS, pages):
        print(f"\n{query}")
        for photo in page:
            print(f"   {photo.urls.small}")


asyncio.run(main())
