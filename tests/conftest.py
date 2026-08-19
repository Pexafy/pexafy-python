import pytest

from pexafy import Client

API = "https://api.pexafy.com/api/v1"


def photo(photo_id="019e0eb8-b028-73cb-9296-dfa70f557bc9", **over):
    d = {
        "photo_id": photo_id,
        "image_url": f"https://cdn.pexafy.com/{photo_id}.jpg",
        "urls": {
            "thumb": f"https://cdn.pexafy.com/{photo_id}_thumb.jpg",
            "small": f"https://cdn.pexafy.com/{photo_id}_small.jpg",
            "regular": f"https://cdn.pexafy.com/{photo_id}_regular.jpg",
            "large": f"https://cdn.pexafy.com/{photo_id}_large.jpg",
            "full": f"https://cdn.pexafy.com/{photo_id}_full.jpg",
        },
        "width": 4000,
        "height": 2667,
        "blur_hash": "LEHV6nWB2yk8pyo0adR*.7kCMdnj",
        "orientation": "landscape",
        "color_name": "blue",
        "color_hex": "#1E90FF",
        "photographer_username": "jdoe",
        "photographer_full_name": "J. Doe",
        "photographer_url": "https://example.com/jdoe",
        "source": "Pexels",
        "license_type": "free",
        "description": "a lake at sunrise",
        "alt_description": "mist rising off a lake at sunrise",
        "uploaded_on": "2024-06-01",
        "relevance_score": 0.81,
        "attribution": {"html": "<a href='#'>J. Doe</a>", "plain": "Photo by J. Doe"},
    }
    d.update(over)
    return d


def envelope(data, *, pagination=None, success=True):
    body = {
        "success": success,
        "data": data,
        "meta": {"request_id": "req_abc123", "took_ms": 61.4},
    }
    if pagination is not None:
        body["pagination"] = pagination
    return body


@pytest.fixture
def client():
    with Client("test-key", max_retries=0) as c:
        yield c
