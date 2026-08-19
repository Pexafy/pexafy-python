from datetime import date

from conftest import photo

from pexafy import Photo


def test_photo_parses_nested_urls_and_dates():
    p = Photo.from_dict(photo())
    assert p.urls.thumb.endswith("_thumb.jpg")
    assert p.uploaded_on == date(2024, 6, 1)
    assert p.attribution.plain == "Photo by J. Doe"


def test_aspect_ratio():
    assert round(Photo.from_dict(photo()).aspect_ratio, 2) == 1.5
    assert Photo.from_dict(photo(width=None, height=None)).aspect_ratio is None


def test_alt_text_falls_back():
    assert Photo.from_dict(photo()).alt_text == "mist rising off a lake at sunrise"
    assert Photo.from_dict(photo(alt_description=None)).alt_text == "a lake at sunrise"
    assert Photo.from_dict(photo(alt_description=None, description=None)).alt_text == ""


def test_unknown_fields_survive_in_raw():
    p = Photo.from_dict(photo(some_future_field="hello"))
    assert p.raw["some_future_field"] == "hello"


def test_bad_date_does_not_raise():
    assert Photo.from_dict(photo(uploaded_on="not a date")).uploaded_on is None
