"""Response objects.

Plain dataclasses rather than a validation library — the dependency footprint
stays at httpx alone, and unknown fields are kept in ``raw`` so a server side
addition never breaks a client that has not been updated yet.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Optional


def _parse_dt(value: Any) -> Optional[datetime]:
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_date(value: Any) -> Optional[date]:
    dt = _parse_dt(value)
    return dt.date() if dt else None


@dataclass
class PhotoUrls:
    """The same image at five widths. Pick the smallest one that fits."""

    thumb: str = ""
    small: str = ""
    regular: str = ""
    large: str = ""
    full: str = ""

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PhotoUrls:
        d = d or {}
        return cls(
            thumb=d.get("thumb", ""),
            small=d.get("small", ""),
            regular=d.get("regular", ""),
            large=d.get("large", ""),
            full=d.get("full", ""),
        )


@dataclass
class Attribution:
    """Credit line for the photographer, ready to drop into a page."""

    html: str = ""
    plain: str = ""

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Attribution:
        d = d or {}
        return cls(html=d.get("html", ""), plain=d.get("plain", ""))


@dataclass
class Photo:
    photo_id: str
    image_url: str = ""
    urls: PhotoUrls = field(default_factory=PhotoUrls)
    width: Optional[int] = None
    height: Optional[int] = None
    blur_hash: Optional[str] = None
    orientation: str = ""
    color_name: str = ""
    color_hex: str = ""
    photographer_username: str = ""
    photographer_full_name: Optional[str] = None
    photographer_url: Optional[str] = None
    source: str = ""
    license_type: str = ""
    source_image_url: Optional[str] = None
    source_description: Optional[str] = None
    description: Optional[str] = None
    alt_description: Optional[str] = None
    uploaded_on: Optional[date] = None
    relevance_score: Optional[float] = None
    attribution: Attribution = field(default_factory=Attribution)
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def aspect_ratio(self) -> Optional[float]:
        if self.width and self.height:
            return self.width / self.height
        return None

    @property
    def alt_text(self) -> str:
        """Best available text for an ``alt`` attribute."""
        return self.alt_description or self.description or self.source_description or ""

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Photo:
        return cls(
            photo_id=d.get("photo_id", ""),
            image_url=d.get("image_url", ""),
            urls=PhotoUrls.from_dict(d.get("urls") or {}),
            width=d.get("width"),
            height=d.get("height"),
            blur_hash=d.get("blur_hash"),
            orientation=d.get("orientation", ""),
            color_name=d.get("color_name", ""),
            color_hex=d.get("color_hex", ""),
            photographer_username=d.get("photographer_username", ""),
            photographer_full_name=d.get("photographer_full_name"),
            photographer_url=d.get("photographer_url"),
            source=d.get("source", ""),
            license_type=d.get("license_type", ""),
            source_image_url=d.get("source_image_url"),
            source_description=d.get("source_description"),
            description=d.get("description"),
            alt_description=d.get("alt_description"),
            uploaded_on=_parse_date(d.get("uploaded_on")),
            relevance_score=d.get("relevance_score"),
            attribution=Attribution.from_dict(d.get("attribution") or {}),
            raw=d,
        )


@dataclass
class Photographer:
    username: str
    full_name: Optional[str] = None
    source: str = ""
    url: Optional[str] = None
    photos_count: int = 0

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Photographer:
        return cls(
            username=d.get("username", ""),
            full_name=d.get("full_name"),
            source=d.get("source", ""),
            url=d.get("url"),
            photos_count=d.get("photos_count", 0),
        )


@dataclass
class Collection:
    id: int
    name: str = ""
    description: Optional[str] = None
    is_public: bool = False
    cover_photo_id: Optional[str] = None
    photos_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Collection:
        return cls(
            id=d.get("id", 0),
            name=d.get("name", ""),
            description=d.get("description"),
            is_public=bool(d.get("is_public", False)),
            cover_photo_id=d.get("cover_photo_id"),
            photos_count=d.get("photos_count", 0),
            created_at=_parse_dt(d.get("created_at")),
            updated_at=_parse_dt(d.get("updated_at")),
        )


@dataclass
class CollectionItem:
    id: int
    photo_id: str
    photo_thumbnail_url: Optional[str] = None
    photo_source: Optional[str] = None
    photo_photographer: Optional[str] = None
    added_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CollectionItem:
        return cls(
            id=d.get("id", 0),
            photo_id=d.get("photo_id", ""),
            photo_thumbnail_url=d.get("photo_thumbnail_url"),
            photo_source=d.get("photo_source"),
            photo_photographer=d.get("photo_photographer"),
            added_at=_parse_dt(d.get("added_at")),
        )


@dataclass
class Pagination:
    next_cursor: Optional[str] = None
    per_page: int = 0
    has_more: bool = False

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Pagination:
        d = d or {}
        return cls(
            next_cursor=d.get("next_cursor"),
            per_page=d.get("per_page", 0),
            has_more=bool(d.get("has_more", False)),
        )


@dataclass
class SearchResult:
    """One page of results.

    Iterating it yields photos, so ``for photo in client.search(...)`` reads the
    way you would expect. Use :meth:`Client.iter_search` to walk every page.
    """

    photos: list[Photo]
    pagination: Pagination
    request_id: str = ""
    took_ms: Optional[float] = None

    def __iter__(self):
        return iter(self.photos)

    def __len__(self) -> int:
        return len(self.photos)

    def __getitem__(self, index: int) -> Photo:
        return self.photos[index]

    @property
    def next_cursor(self) -> Optional[str]:
        return self.pagination.next_cursor

    @property
    def has_more(self) -> bool:
        return self.pagination.has_more
