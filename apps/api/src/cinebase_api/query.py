"""`/movies` parameters and opaque keyset cursors (TECHNICAL_SPEC §5)."""

import base64
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from .errors import ApiError
from .schemas import EXCLUSIONS, SORTS

MAX_QUERY_LENGTH = 200
DEFAULT_LIMIT = 24
MAX_LIMIT = 48

SortKey = list[str | int]


@dataclass(frozen=True)
class MovieQuery:
    q: str = ""
    genres: tuple[str, ...] = ()
    year_from: int | None = None
    year_to: int | None = None
    runtime_max: int | None = None
    exclude: tuple[str, ...] = ()
    sort: str = "notable"
    limit: int = DEFAULT_LIMIT
    cursor: str | None = field(default=None, compare=False)

    def key(self) -> str:
        """Everything that changes which films appear and in what order."""
        parts = [
            f"q={self.q}",
            f"genre={','.join(sorted(self.genres))}",
            f"year_from={self.year_from}",
            f"year_to={self.year_to}",
            f"runtime_max={self.runtime_max}",
            f"exclude={','.join(sorted(self.exclude))}",
            f"sort={self.sort}",
        ]
        return "&".join(parts)


def default_sort(q: str) -> str:
    return "relevance" if q else "notable"


def _parse_int(raw: str | None, name: str, errors: dict[str, str]) -> int | None:
    if raw is None or raw.strip() == "":
        return None
    text = raw.strip()
    if not (text.lstrip("-").isdigit() and text.count("-") <= 1 and not text.endswith("-")):
        errors[name] = "Must be a whole number."
        return None
    return int(text)


def _split(values: list[str]) -> tuple[str, ...]:
    seen: dict[str, None] = {}
    for value in values:
        for part in value.split(","):
            if part.strip():
                seen[part.strip()] = None
    return tuple(seen)


def parse_movie_query(
    q: str | None,
    genre: list[str],
    year_from: str | None,
    year_to: str | None,
    runtime_max: str | None,
    exclude: list[str],
    sort: str | None,
    limit: str | None,
    cursor: str | None,
) -> MovieQuery:
    """Same rules as the web's parseMovieQuery; every invalid field is reported in one 422."""
    errors: dict[str, str] = {}
    text = (q or "").strip()
    if len(text) > MAX_QUERY_LENGTH:
        errors["q"] = f"Must be at most {MAX_QUERY_LENGTH} characters."

    y_from = _parse_int(year_from, "year_from", errors)
    y_to = _parse_int(year_to, "year_to", errors)
    if y_from is not None and y_to is not None and y_from > y_to:
        errors["year_to"] = "Must be greater than or equal to year_from."

    r_max = _parse_int(runtime_max, "runtime_max", errors)
    if r_max is not None and r_max <= 0:
        errors["runtime_max"] = "Must be a positive number of minutes."

    excludes = _split(exclude)
    unknown = [e for e in excludes if e not in EXCLUSIONS]
    if unknown:
        errors["exclude"] = f"Must be one of: {', '.join(EXCLUSIONS)}."

    chosen = default_sort(text)
    if sort:
        if sort in SORTS:
            chosen = sort
        else:
            errors["sort"] = f"Must be one of: {', '.join(SORTS)}."
    if chosen == "relevance" and not text:
        errors["sort"] = "relevance requires a non-empty q."

    size = _parse_int(limit, "limit", errors)
    size = DEFAULT_LIMIT if size is None else size
    if not 1 <= size <= MAX_LIMIT:
        errors["limit"] = f"Must be between 1 and {MAX_LIMIT}."

    if errors:
        raise ApiError(422, "invalid_parameters", "Some search parameters are invalid.", errors)
    return MovieQuery(
        q=text,
        genres=_split(genre),
        year_from=y_from,
        year_to=y_to,
        runtime_max=r_max,
        exclude=excludes,
        sort=chosen,
        limit=size,
        cursor=cursor or None,
    )


def _fingerprint(query: MovieQuery) -> str:
    return hashlib.sha256(query.key().encode()).hexdigest()[:12]


def encode_cursor(query: MovieQuery, catalog_version: str, last_key: SortKey) -> str:
    payload = {"v": 1, "f": _fingerprint(query), "cv": catalog_version, "k": last_key}
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(token: str, query: MovieQuery, catalog_version: str) -> SortKey:
    invalid = ApiError(400, "invalid_cursor", "This page link is no longer valid. Start the list again.")
    try:
        payload: Any = json.loads(base64.urlsafe_b64decode(token + "=" * (-len(token) % 4)))
    except (ValueError, UnicodeDecodeError):
        raise invalid from None
    if (
        not isinstance(payload, dict)
        or payload.get("v") != 1
        or payload.get("f") != _fingerprint(query)
        or payload.get("cv") != catalog_version
        or not isinstance(payload.get("k"), list)
        or not all(isinstance(p, str | int) and not isinstance(p, bool) for p in payload["k"])
    ):
        raise invalid
    return list(payload["k"])
