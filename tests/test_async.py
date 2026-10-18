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


def _public_methods(cls):
    return {name for name in dir(cls) if not name.startswith("_") and callable(getattr(cls, name))}


def test_async_client_has_every_method_of_the_sync_client():
    from pexafy import Client

    # close / aclose are the one intended difference.
    assert _public_methods(Client) - {"close"} == _public_methods(AsyncClient) - {"aclose"}


@respx.mock
async def test_async_collections_roundtrip():
    respx.post(f"{API}/collections").mock(return_value=httpx.Response(
        200, json=envelope({"id": 7, "name": "moodboard", "is_public": False,
                            "photos_count": 0, "created_at": "2026-08-19T10:00:00Z"})))
    respx.post(f"{API}/collections/7/photos").mock(return_value=httpx.Response(
        200, json=envelope({"id": 1, "photo_id": "abc", "added_at": "2026-08-19T10:01:00Z"})))
    respx.delete(f"{API}/collections/7/photos/abc").mock(
        return_value=httpx.Response(200, json=envelope(None)))
    async with AsyncClient("k", max_retries=0) as client:
        assert (await client.create_collection("moodboard")).id == 7
        assert (await client.add_to_collection(7, "abc")).photo_id == "abc"
        await client.remove_from_collection(7, "abc")


@respx.mock
async def test_async_usage_history_and_photographers():
    daily = respx.get(f"{API}/usage/daily").mock(
        return_value=httpx.Response(200, json=envelope({"days": []})))
    respx.get(f"{API}/facets/photographers/suggest").mock(return_value=httpx.Response(
        200, json=envelope([{"username": "jdoe", "full_name": "J. Doe"}])))
    async with AsyncClient("k", max_retries=0) as client:
        await client.usage_daily(days=7)
        names = [p.username for p in await client.suggest_photographers("jd")]
    assert daily.calls.last.request.url.params["days"] == "7"
    assert names == ["jdoe"]
