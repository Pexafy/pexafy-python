"""Python client for the Pexafy image search API.

    from pexafy import Client

    client = Client("your-api-key")
    for photo in client.search("a quiet street in the rain", per_page=10):
        print(photo.urls.regular)

Get a key at https://pexafy.com — the free tier does not need a card.
"""

__version__ = "0.1.2"

from .client import DEFAULT_BASE_URL, AsyncClient, Client
from .errors import (
    APIError,
    AuthenticationError,
    ConnectionError_,
    NotFoundError,
    PermissionError_,
    PexafyError,
    RateLimitError,
    ServerError,
    TimeoutError_,
    ValidationError,
)
from .models import (
    Attribution,
    Collection,
    CollectionItem,
    Pagination,
    Photo,
    Photographer,
    PhotoUrls,
    SearchResult,
)

__all__ = [
    "Client",
    "AsyncClient",
    "DEFAULT_BASE_URL",
    "Photo",
    "PhotoUrls",
    "Attribution",
    "Photographer",
    "Collection",
    "CollectionItem",
    "Pagination",
    "SearchResult",
    "PexafyError",
    "APIError",
    "AuthenticationError",
    "PermissionError_",
    "NotFoundError",
    "RateLimitError",
    "ValidationError",
    "ServerError",
    "TimeoutError_",
    "ConnectionError_",
    "__version__",
]
