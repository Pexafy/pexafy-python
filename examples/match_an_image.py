"""Find photos that look like one you already have.

Useful for building a moodboard around a reference, or finding an alternative
to an image you cannot license.

    PEXAFY_API_KEY=... python match_an_image.py reference.jpg
"""

import sys

from pexafy import Client

reference = sys.argv[1]

with Client() as client:
    result = client.search_by_image(reference, per_page=8)

    for photo in result:
        print(f"{photo.relevance_score:.3f}  {photo.color_name:<8} {photo.urls.small}")

    # If you plan to keep going from one of these, use its id rather than
    # uploading the image again — no encoding round trip.
    if len(result):
        more = client.similar(result[0].photo_id, per_page=8)
        print(f"\n{len(more)} more like the top result")
