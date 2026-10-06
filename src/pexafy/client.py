"""Synchronous and asynchronous clients for the Pexafy API."""

from __future__ import annotations

import os
import random
import time
from collections.abc import AsyncIterator, Iterator, Sequence
from pathlib import Path
from typing import Any, BinaryIO, Optional, Union

import httpx

from . import errors
from .models import (
    Collection,
    CollectionItem,
    Pagination,
    Photo,
    Photographer,
    SearchResult,
)

__all__ = ["Client", "AsyncClient", "DEFAULT_BASE_URL"]

DEFAULT_BASE_URL = "https://api.pexafy.com"
DEFAULT_TIMEOUT = 30.0
DEFAULT_RETRIES = 2
RETRY_STATUS = {429, 500, 502, 503, 504}

ImageInput = Union[str, Path, bytes, BinaryIO]


def _csv(value: Union[str, Sequence[str], None]) -> Optional[str]:
    """Join a field selection into the comma separated string `fields` expects."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return ",".join(str(v) for v in value)


def _multi(value: Union[str, Sequence[str], None]) -> Optional[list]:
    """Normalise a multi-valued filter into a list.

    `orientation`, `source` and `license_type` are declared server-side as
    repeated query parameters, so a list has to go out as ?source=a&source=b.
    Sending "a,b" as one value matches nothing (source, license_type) or is
    dropped altogether (orientation), and neither failure says anything. A
    comma separated string is accepted here for convenience and split.
    """
    if value is None:
        return None
    if isinstance(value, str):
        values = [v.strip() for v in value.split(",")]
    else:
        values = [str(v).strip() for v in value]
    values = [v for v in values if v]
    return values or None


def _single(name: str, value: Any) -> Optional[str]:
    """Guard a filter the API accepts only once.

    Passing several values would not fail: the server keeps the last one and
    filters on that, so the caller gets a plausible-looking result set built
    from a filter they did not ask for.
    """
    if value is None or isinstance(value, str):
        return value
    raise TypeError(
        f"{name} takes a single value, got {value!r}. "
        f"The API filters on one {name} at a time."
    )


def _clean(params: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in params.items() if v is not None}


def _open_image(image: ImageInput) -> tuple[str, Any]:
    """Normalise the several things a caller might hand us into a file tuple."""
    if isinstance(image, (str, Path)):
        path = Path(image)
        return path.name, path.read_bytes()
    if isinstance(image, bytes):
        return "query.jpg", image
    name = getattr(image, "name", "query.jpg")
    return Path(str(name)).name, image.read()


class _Base:
    """Everything that does not touch the network."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_RETRIES,
    ) -> None:
        key = api_key or os.environ.get("PEXAFY_API_KEY")
        if not key:
            raise errors.PexafyError(
                "No API key. Pass api_key= or set PEXAFY_API_KEY. "
                "Keys are created at https://pexafy.com/dashboard/"
            )
        self.api_key = key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

    @property
    def _headers(self) -> dict[str, str]:
        from . import __version__

        return {
            "x-api-key": self.api_key,
            "accept": "application/json",
            "user-agent": f"pexafy-python/{__version__}",
        }

    def _url(self, path: str) -> str:
        return f"{self.base_url}/api/v1{path}"

    @staticmethod
    def _should_retry(response: httpx.Response) -> bool:
        """A 5xx is retried; a 429 only when it is the per-minute rate limit.

        The API also answers 429 when the daily or monthly quota is spent
        (`DAILY_QUOTA_EXCEEDED`, `QUOTA_EXCEEDED`). Waiting a minute cannot clear
        those — the daily one comes back at midnight UTC — so they raise at once
        instead of stalling the caller through the retries.
        """
        if response.status_code != 429:
            return response.status_code in RETRY_STATUS
        try:
            code = (response.json().get("error") or {}).get("code")
        except (ValueError, AttributeError):
            code = None
        if code:
            return code == "RATE_LIMITED"
        header = response.headers.get("retry-after")
        try:
            return header is None or float(header) <= 60
        except ValueError:
            return True

    @staticmethod
    def _retry_delay(attempt: int, response: Optional[httpx.Response]) -> float:
        """Honour Retry-After when the server sends one, back off otherwise."""
        if response is not None:
            header = response.headers.get("retry-after")
            if header:
                try:
                    return min(float(header), 60.0)
                except ValueError:
                    pass
        return min(2.0**attempt, 30.0) + random.random() * 0.3

    def _unwrap(self, response: httpx.Response) -> dict[str, Any]:
        """Turn the response envelope into data, or raise the right error."""
        try:
            body = response.json()
        except ValueError:
            body = {}

        if response.is_success and body.get("success", True):
            return body

        err = body.get("error") or {}
        message = (
            err.get("message") or body.get("detail")
            or response.reason_phrase or "request failed"
        )
        if isinstance(message, list):  # FastAPI validation detail
            message = "; ".join(str(m.get("msg", m)) for m in message)

        exc_class = errors.from_status(response.status_code)
        kwargs: dict[str, Any] = {
            "status_code": response.status_code,
            "code": err.get("code"),
            "request_id": err.get("request_id") or (body.get("meta") or {}).get("request_id"),
            "payload": body,
        }
        if exc_class is errors.RateLimitError:
            retry_after = response.headers.get("retry-after")
            kwargs["retry_after"] = float(retry_after) if retry_after else None
        raise exc_class(str(message), **kwargs)

    @staticmethod
    def _to_search_result(body: dict[str, Any]) -> SearchResult:
        meta = body.get("meta") or {}
        return SearchResult(
            photos=[Photo.from_dict(p) for p in body.get("data") or []],
            pagination=Pagination.from_dict(body.get("pagination") or {}),
            request_id=meta.get("request_id", ""),
            took_ms=meta.get("took_ms"),
        )

    def _search_params(
        self,
        q: Optional[str],
        *,
        color_name=None, color_hex=None, color_tolerance=None,
        orientation=None, source=None, license_type=None, photographer=None,
        per_page=None, limit=None, score_threshold=None, cursor=None,
        fields=None, after_date=None, sort_by=None,
    ) -> dict[str, Any]:
        return _clean({
            "q": q,
            "color_name": _single("color_name", color_name),
            "color_hex": color_hex,
            "color_tolerance": color_tolerance,
            "orientation": _multi(orientation),
            "source": _multi(source),
            "license_type": _multi(license_type),
            "photographer": photographer,
            "per_page": per_page,
            "limit": limit,
            "score_threshold": score_threshold,
            "cursor": cursor,
            "fields": _csv(fields),
            "after_date": str(after_date) if after_date else None,
            "sort_by": sort_by,
        })


class Client(_Base):
    """Blocking client.

    >>> from pexafy import Client
    >>> client = Client("your-api-key")
    >>> for photo in client.search("sunrise over a foggy valley", per_page=5):
    ...     print(photo.photo_id, photo.urls.regular)

    Safe to keep around for the lifetime of your process; it holds one
    connection pool. Close it when you are done, or use it as a context
    manager.
    """

    def __init__(self, api_key: Optional[str] = None, **kwargs: Any) -> None:
        super().__init__(api_key, **kwargs)
        self._http = httpx.Client(timeout=self.timeout, headers=self._headers)

    def __enter__(self) -> Client:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        url = self._url(path)
        last_response: Optional[httpx.Response] = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self._http.request(method, url, **kwargs)
            except httpx.TimeoutException as exc:
                if attempt >= self.max_retries:
                    raise errors.TimeoutError_(
                        f"{method} {path} timed out after {self.timeout}s"
                    ) from exc
                time.sleep(self._retry_delay(attempt, None))
                continue
            except httpx.TransportError as exc:
                if attempt >= self.max_retries:
                    raise errors.ConnectionError_(
                        f"could not reach {self.base_url}: {exc}"
                    ) from exc
                time.sleep(self._retry_delay(attempt, None))
                continue

            if self._should_retry(response) and attempt < self.max_retries:
                last_response = response
                time.sleep(self._retry_delay(attempt, response))
                continue
            return self._unwrap(response)

        return self._unwrap(last_response)  # pragma: no cover - loop always returns

    # -- search ---------------------------------------------------------

    def search(self, q: str, **filters: Any) -> SearchResult:
        """Search by description.

        Write what you would say to a person: `two people hiking on a ridge at
        dawn` works better than `hiking dawn`. The engine matches meaning, so
        keyword stuffing makes results worse, not better.
        """
        params = self._search_params(q, **filters)
        return self._to_search_result(self._request("GET", "/search/photos", params=params))

    def iter_search(
        self, q: str, *, max_results: Optional[int] = None, **filters: Any
    ) -> Iterator[Photo]:
        """Walk every page, following the cursor for you."""
        seen = 0
        cursor = filters.pop("cursor", None)
        while True:
            page = self.search(q, cursor=cursor, **filters)
            for photo in page.photos:
                yield photo
                seen += 1
                if max_results is not None and seen >= max_results:
                    return
            if not page.has_more or not page.next_cursor:
                return
            cursor = page.next_cursor

    def search_by_image(self, image: ImageInput, **filters: Any) -> SearchResult:
        """Find photos that look like the one you pass in.

        Accepts a path, raw bytes, or an open binary file.
        """
        filename, content = _open_image(image)
        params = self._search_params(None, **filters)
        body = self._request(
            "POST", "/search/photos",
            files={"image": (filename, content)},
            params=params,
        )
        return self._to_search_result(body)

    # -- photos ---------------------------------------------------------

    def get_photo(self, photo_id: str) -> Photo:
        return Photo.from_dict(self._request("GET", f"/photos/{photo_id}")["data"])

    def similar(self, photo_id: str, **filters: Any) -> SearchResult:
        params = self._search_params(None, **filters)
        return self._to_search_result(
            self._request("GET", f"/photos/{photo_id}/similar", params=params)
        )

    # -- facets ---------------------------------------------------------

    def colors(self) -> list[dict[str, Any]]:
        return self._request("GET", "/facets/colors")["data"]

    def sources(self) -> list[dict[str, Any]]:
        return self._request("GET", "/facets/sources")["data"]

    def orientations(self) -> list[dict[str, Any]]:
        return self._request("GET", "/facets/orientations")["data"]

    def licenses(self) -> list[dict[str, Any]]:
        return self._request("GET", "/facets/licenses")["data"]

    def suggest_photographers(self, q: str, *, limit: Optional[int] = None) -> list[Photographer]:
        params = _clean({"q": q, "limit": limit})
        data = self._request("GET", "/facets/photographers/suggest", params=params)["data"]
        return [Photographer.from_dict(p) for p in data]

    def photographer(self, username: str) -> list[Photographer]:
        data = self._request("GET", f"/facets/photographers/{username}")["data"]
        return [Photographer.from_dict(p) for p in data]

    # -- collections ----------------------------------------------------

    def collections(self) -> list[Collection]:
        return [Collection.from_dict(c) for c in self._request("GET", "/collections")["data"]]

    def create_collection(
        self, name: str, *, description: Optional[str] = None, is_public: bool = False
    ) -> Collection:
        body = _clean({"name": name, "description": description, "is_public": is_public})
        return Collection.from_dict(self._request("POST", "/collections", json=body)["data"])

    def collection(self, collection_id: int) -> Collection:
        return Collection.from_dict(self._request("GET", f"/collections/{collection_id}")["data"])

    def delete_collection(self, collection_id: int) -> None:
        self._request("DELETE", f"/collections/{collection_id}")

    def add_to_collection(self, collection_id: int, photo_id: str) -> CollectionItem:
        body = self._request(
            "POST", f"/collections/{collection_id}/photos", json={"photo_id": photo_id}
        )
        return CollectionItem.from_dict(body["data"])

    def remove_from_collection(self, collection_id: int, photo_id: str) -> None:
        self._request("DELETE", f"/collections/{collection_id}/photos/{photo_id}")

    # -- usage ----------------------------------------------------------

    def usage(self) -> dict[str, Any]:
        return self._request("GET", "/usage")["data"]

    def usage_daily(self) -> dict[str, Any]:
        return self._request("GET", "/usage/daily")["data"]

    def usage_monthly(self) -> dict[str, Any]:
        return self._request("GET", "/usage/monthly")["data"]

    def usage_by_key(self) -> dict[str, Any]:
        return self._request("GET", "/usage/by-key")["data"]


class AsyncClient(_Base):
    """Same surface as :class:`Client`, awaitable.

    >>> async with AsyncClient() as client:
    ...     page = await client.search("empty office at night")
    """

    def __init__(self, api_key: Optional[str] = None, **kwargs: Any) -> None:
        super().__init__(api_key, **kwargs)
        self._http = httpx.AsyncClient(timeout=self.timeout, headers=self._headers)

    async def __aenter__(self) -> AsyncClient:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        import asyncio

        url = self._url(path)
        last_response: Optional[httpx.Response] = None
        for attempt in range(self.max_retries + 1):
            try:
                response = await self._http.request(method, url, **kwargs)
            except httpx.TimeoutException as exc:
                if attempt >= self.max_retries:
                    raise errors.TimeoutError_(
                        f"{method} {path} timed out after {self.timeout}s"
                    ) from exc
                await asyncio.sleep(self._retry_delay(attempt, None))
                continue
            except httpx.TransportError as exc:
                if attempt >= self.max_retries:
                    raise errors.ConnectionError_(
                        f"could not reach {self.base_url}: {exc}"
                    ) from exc
                await asyncio.sleep(self._retry_delay(attempt, None))
                continue

            if self._should_retry(response) and attempt < self.max_retries:
                last_response = response
                await asyncio.sleep(self._retry_delay(attempt, response))
                continue
            return self._unwrap(response)

        return self._unwrap(last_response)  # pragma: no cover

    async def search(self, q: str, **filters: Any) -> SearchResult:
        params = self._search_params(q, **filters)
        return self._to_search_result(await self._request("GET", "/search/photos", params=params))

    async def iter_search(
        self, q: str, *, max_results: Optional[int] = None, **filters: Any
    ) -> AsyncIterator[Photo]:
        seen = 0
        cursor = filters.pop("cursor", None)
        while True:
            page = await self.search(q, cursor=cursor, **filters)
            for photo in page.photos:
                yield photo
                seen += 1
                if max_results is not None and seen >= max_results:
                    return
            if not page.has_more or not page.next_cursor:
                return
            cursor = page.next_cursor

    async def search_by_image(self, image: ImageInput, **filters: Any) -> SearchResult:
        filename, content = _open_image(image)
        params = self._search_params(None, **filters)
        body = await self._request(
            "POST", "/search/photos", files={"image": (filename, content)}, params=params
        )
        return self._to_search_result(body)

    async def get_photo(self, photo_id: str) -> Photo:
        body = await self._request("GET", f"/photos/{photo_id}")
        return Photo.from_dict(body["data"])

    async def similar(self, photo_id: str, **filters: Any) -> SearchResult:
        params = self._search_params(None, **filters)
        body = await self._request("GET", f"/photos/{photo_id}/similar", params=params)
        return self._to_search_result(body)

    async def colors(self) -> list[dict[str, Any]]:
        return (await self._request("GET", "/facets/colors"))["data"]

    async def sources(self) -> list[dict[str, Any]]:
        return (await self._request("GET", "/facets/sources"))["data"]

    async def orientations(self) -> list[dict[str, Any]]:
        return (await self._request("GET", "/facets/orientations"))["data"]

    async def licenses(self) -> list[dict[str, Any]]:
        return (await self._request("GET", "/facets/licenses"))["data"]

    async def usage(self) -> dict[str, Any]:
        return (await self._request("GET", "/usage"))["data"]
