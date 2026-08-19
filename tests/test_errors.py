import httpx
import pytest
import respx
from conftest import API

from pexafy import Client, errors


def error_body(code, message):
    return {"success": False, "data": None,
            "meta": {"request_id": "req_zzz"},
            "error": {"code": code, "message": message, "request_id": "req_zzz"}}


@pytest.mark.parametrize("status,expected", [
    (401, errors.AuthenticationError),
    (403, errors.PermissionError_),
    (404, errors.NotFoundError),
    (422, errors.ValidationError),
    (429, errors.RateLimitError),
    (500, errors.ServerError),
    (503, errors.ServerError),
])
@respx.mock
def test_status_maps_to_exception(client, status, expected):
    respx.get(f"{API}/search/photos").mock(
        return_value=httpx.Response(status, json=error_body("some_code", "nope"))
    )
    with pytest.raises(expected) as exc:
        client.search("x")
    assert exc.value.status_code == status
    assert exc.value.code == "some_code"
    assert exc.value.request_id == "req_zzz"


@respx.mock
def test_rate_limit_exposes_retry_after(client):
    respx.get(f"{API}/search/photos").mock(
        return_value=httpx.Response(429, headers={"retry-after": "12"},
                                    json=error_body("quota_exceeded", "monthly quota reached"))
    )
    with pytest.raises(errors.RateLimitError) as exc:
        client.search("x")
    assert exc.value.retry_after == 12.0


@respx.mock
def test_timeout_is_wrapped(client):
    respx.get(f"{API}/search/photos").mock(side_effect=httpx.ReadTimeout("too slow"))
    with pytest.raises(errors.TimeoutError_):
        client.search("x")


@respx.mock
def test_connection_failure_is_wrapped(client):
    respx.get(f"{API}/search/photos").mock(side_effect=httpx.ConnectError("no route"))
    with pytest.raises(errors.ConnectionError_):
        client.search("x")


@respx.mock
def test_server_errors_are_retried_then_succeed():
    respx.get(f"{API}/search/photos").mock(side_effect=[
        httpx.Response(503, json=error_body("unavailable", "try later")),
        httpx.Response(200, json={"success": True, "data": [], "meta": {}}),
    ])
    with Client("k", max_retries=1) as client:
        assert len(client.search("x")) == 0


def test_missing_key_is_refused_early(monkeypatch):
    monkeypatch.delenv("PEXAFY_API_KEY", raising=False)
    with pytest.raises(errors.PexafyError, match="No API key"):
        Client()


def test_key_can_come_from_the_environment(monkeypatch):
    monkeypatch.setenv("PEXAFY_API_KEY", "from-env")
    with Client() as client:
        assert client.api_key == "from-env"
