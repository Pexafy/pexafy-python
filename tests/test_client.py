import httpx
import pytest
import respx
from conftest import API, envelope, photo


@respx.mock
def test_search_returns_photos(client):
    route = respx.get(f"{API}/search/photos").mock(
        return_value=httpx.Response(200, json=envelope(
            [photo()], pagination={"next_cursor": "c2", "per_page": 20, "has_more": True}
        ))
    )
    result = client.search("a lake at sunrise", per_page=20)

    assert route.called
    assert len(result) == 1
    assert result[0].photographer_username == "jdoe"
    assert result[0].urls.regular.endswith("_regular.jpg")
    assert result.has_more is True
    assert result.next_cursor == "c2"
    assert result.request_id == "req_abc123"


@respx.mock
def test_api_key_goes_in_the_header(client):
    route = respx.get(f"{API}/search/photos").mock(
        return_value=httpx.Response(200, json=envelope([]))
    )
    client.search("anything")
    assert route.calls[0].request.headers["x-api-key"] == "test-key"


@respx.mock
def test_list_filters_are_sent_as_repeated_parameters(client):
    """?source=a&source=b, not ?source=a,b.

    The comma separated form reaches the server as one value: it matches no
    source and no licence, and an unknown orientation is dropped instead of
    filtering, so the caller silently gets an unfiltered page back.
    """
    route = respx.get(f"{API}/search/photos").mock(
        return_value=httpx.Response(200, json=envelope([]))
    )
    client.search("x", source=["Pexels", "Unsplash"], orientation=["landscape", "square"])

    params = route.calls[0].request.url.params
    assert params.get_list("source") == ["Pexels", "Unsplash"]
    assert params.get_list("orientation") == ["landscape", "square"]


@respx.mock
def test_a_comma_separated_string_is_split_into_repeated_parameters(client):
    route = respx.get(f"{API}/search/photos").mock(
        return_value=httpx.Response(200, json=envelope([]))
    )
    client.search("x", source="Pexels, Unsplash")

    assert route.calls[0].request.url.params.get_list("source") == ["Pexels", "Unsplash"]


def test_several_colours_are_refused_rather_than_silently_narrowed(client):
    """The server keeps the last color_name and filters on it without saying so."""
    with pytest.raises(TypeError, match="color_name takes a single value"):
        client.search("x", color_name=["blue", "red"])


@respx.mock
def test_fields_stays_comma_separated(client):
    route = respx.get(f"{API}/search/photos").mock(
        return_value=httpx.Response(200, json=envelope([]))
    )
    client.search("x", fields=["photo_id", "urls"])

    assert route.calls[0].request.url.params["fields"] == "photo_id,urls"


@respx.mock
def test_none_filters_are_dropped(client):
    route = respx.get(f"{API}/search/photos").mock(
        return_value=httpx.Response(200, json=envelope([]))
    )
    client.search("x", color_name=None, per_page=5)

    params = route.calls[0].request.url.params
    assert "color_name" not in params
    assert params["per_page"] == "5"


@respx.mock
def test_iter_search_follows_the_cursor(client):
    pages = [
        httpx.Response(200, json=envelope(
            [photo("a")], pagination={"next_cursor": "c2", "per_page": 1, "has_more": True})),
        httpx.Response(200, json=envelope(
            [photo("b")], pagination={"next_cursor": None, "per_page": 1, "has_more": False})),
    ]
    respx.get(f"{API}/search/photos").mock(side_effect=pages)

    ids = [p.photo_id for p in client.iter_search("x", per_page=1)]
    assert ids == ["a", "b"]


@respx.mock
def test_iter_search_stops_at_max_results(client):
    respx.get(f"{API}/search/photos").mock(
        return_value=httpx.Response(200, json=envelope(
            [photo("a"), photo("b"), photo("c")],
            pagination={"next_cursor": "c2", "per_page": 3, "has_more": True}))
    )
    assert len(list(client.iter_search("x", max_results=2))) == 2


@respx.mock
def test_search_by_image_posts_multipart(client, tmp_path):
    image = tmp_path / "query.jpg"
    image.write_bytes(b"\xff\xd8\xff\xe0 not really a jpeg")
    route = respx.post(f"{API}/search/photos").mock(
        return_value=httpx.Response(200, json=envelope([photo()]))
    )
    result = client.search_by_image(image)

    assert len(result) == 1
    assert b"query.jpg" in route.calls[0].request.content


@respx.mock
def test_search_by_image_accepts_bytes(client):
    route = respx.post(f"{API}/search/photos").mock(
        return_value=httpx.Response(200, json=envelope([]))
    )
    client.search_by_image(b"\xff\xd8\xff\xe0")
    assert route.called


@respx.mock
def test_get_photo(client):
    respx.get(f"{API}/photos/abc").mock(
        return_value=httpx.Response(200, json=envelope(photo("abc")))
    )
    assert client.get_photo("abc").photo_id == "abc"


@respx.mock
def test_similar(client):
    respx.get(f"{API}/photos/abc/similar").mock(
        return_value=httpx.Response(200, json=envelope([photo("d")]))
    )
    assert [p.photo_id for p in client.similar("abc")] == ["d"]


@respx.mock
def test_collections_roundtrip(client):
    respx.post(f"{API}/collections").mock(return_value=httpx.Response(
        200, json=envelope({"id": 7, "name": "moodboard", "is_public": False,
                            "photos_count": 0, "created_at": "2026-08-19T10:00:00Z"})))
    collection = client.create_collection("moodboard")
    assert collection.id == 7
    assert collection.created_at.year == 2026

    respx.post(f"{API}/collections/7/photos").mock(return_value=httpx.Response(
        200, json=envelope({"id": 1, "photo_id": "abc", "added_at": "2026-08-19T10:01:00Z"})))
    assert client.add_to_collection(7, "abc").photo_id == "abc"
