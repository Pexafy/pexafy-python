"""Command line interface.

    pexafy search "morning fog over pine trees" -n 5
    pexafy photo 019e0eb8-b028-73cb-9296-dfa70f557bc9
    pexafy similar 019e0eb8-b028-73cb-9296-dfa70f557bc9
    pexafy usage

Reads the key from PEXAFY_API_KEY.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from . import __version__, errors
from .client import Client


def _print_photos(photos: list[Any], as_json: bool) -> None:
    if as_json:
        json.dump([p.raw for p in photos], sys.stdout, indent=2)
        sys.stdout.write("\n")
        return
    for p in photos:
        score = f"{p.relevance_score:.3f}" if p.relevance_score is not None else "  -  "
        size = f"{p.width}x{p.height}" if p.width else ""
        print(
            f"{score}  {p.photo_id}  {size:>11}  "
            f"{p.color_name:<10} {p.source:<10} {p.urls.regular}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pexafy", description="Search stock photos from the terminal."
    )
    parser.add_argument("--version", action="version", version=f"pexafy {__version__}")
    parser.add_argument("--json", action="store_true", help="raw JSON instead of a table")
    sub = parser.add_subparsers(dest="command", required=True)

    s = sub.add_parser("search", help="search by description")
    s.add_argument("query")
    s.add_argument("-n", "--per-page", type=int, default=10)
    s.add_argument("--color")
    s.add_argument("--orientation")
    s.add_argument("--source")

    p = sub.add_parser("photo", help="fetch one photo")
    p.add_argument("photo_id")

    sim = sub.add_parser("similar", help="photos that look like this one")
    sim.add_argument("photo_id")
    sim.add_argument("-n", "--per-page", type=int, default=10)

    sub.add_parser("usage", help="current month usage")

    args = parser.parse_args(argv)

    try:
        with Client() as client:
            if args.command == "search":
                result = client.search(
                    args.query,
                    per_page=args.per_page,
                    color_name=args.color,
                    orientation=args.orientation,
                    source=args.source,
                )
                _print_photos(result.photos, args.json)
            elif args.command == "photo":
                photo = client.get_photo(args.photo_id)
                _print_photos([photo], args.json)
            elif args.command == "similar":
                result = client.similar(args.photo_id, per_page=args.per_page)
                _print_photos(result.photos, args.json)
            elif args.command == "usage":
                json.dump(client.usage(), sys.stdout, indent=2)
                sys.stdout.write("\n")
    except errors.PexafyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
