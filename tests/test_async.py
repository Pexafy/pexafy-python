import httpx
import respx
from conftest import API, envelope, photo

from pexafy import AsyncClient


@respx.mock
async def test_async_search():
    respx.get(f"{API}/search/photos").mock(
        return_value=httpx.Response(200, json=envelope([photo()]))
    )
    async with AsyncClient("k") as client:
        result = await client.search("x")
    assert len(result) == 1


@respx.mock
async def test_async_iter_search_follows_cursor():
    respx.get(f"{API}/search/photos").mock(side_effect=[
        httpx.Response(200, json=envelope(
            [photo("a")], pagination={"next_cursor": "c2", "per_page": 1, "has_more": True})),
        httpx.Response(200, json=envelope(
            [photo("b")], pagination={"next_cursor": None, "per_page": 1, "has_more": False})),
    ])
    async with AsyncClient("k") as client:
        ids = [p.photo_id async for p in client.iter_search("x", per_page=1)]
    assert ids == ["a", "b"]
