"""Exceptions raised by the client."""

from __future__ import annotations

from typing import Any, Optional


class PexafyError(Exception):
    """Base class for everything this package raises."""


class APIError(PexafyError):
    """The API answered, but with an error.

    ``code`` is the machine readable identifier from the response envelope when
    the server sent one; it is stable across versions and safe to branch on.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        code: Optional[str] = None,
        request_id: Optional[str] = None,
        payload: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.request_id = request_id
        self.payload = payload or {}

    def __str__(self) -> str:
        bits = [self.message]
        if self.status_code:
            bits.append(f"(HTTP {self.status_code}")
            if self.code:
                bits[-1] += f", {self.code}"
            bits[-1] += ")"
        if self.request_id:
            bits.append(f"request_id={self.request_id}")
        return " ".join(bits)


class AuthenticationError(APIError):
    """Missing, malformed or revoked API key."""


class PermissionError_(APIError):
    """The key is valid but lacks the scope for this call."""


class NotFoundError(APIError):
    """No such photo, collection or photographer."""


class RateLimitError(APIError):
    """Too many requests, or the plan quota is exhausted.

    ``retry_after`` is the number of seconds the server asked us to wait, when
    it said so.
    """

    def __init__(self, *args: Any, retry_after: Optional[float] = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.retry_after = retry_after


class ValidationError(APIError):
    """The request was rejected before it reached the search engine."""


class ServerError(APIError):
    """Something broke on our side. These are the ones worth retrying."""


class TimeoutError_(PexafyError):
    """The request took longer than the configured timeout."""


class ConnectionError_(PexafyError):
    """The API could not be reached at all."""


STATUS_MAP = {
    400: ValidationError,
    401: AuthenticationError,
    403: PermissionError_,
    404: NotFoundError,
    422: ValidationError,
    429: RateLimitError,
}


def from_status(status: int) -> type[APIError]:
    if status in STATUS_MAP:
        return STATUS_MAP[status]
    if status >= 500:
        return ServerError
    return APIError
