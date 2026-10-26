"""What a provider hands to the importer: complete film records keyed by (provider, external_id)."""

import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Protocol

NAMESPACE = uuid.UUID("6f1c5a52-5d0e-4c55-9d3b-6c1b0f0c1e8a")


def stable_id(provider: str, external_id: str) -> uuid.UUID:
    """Deterministic UUID for a record first seen from this provider. Re-imports find films by external ID."""
    return uuid.uuid5(NAMESPACE, f"{provider}:{external_id}")


@dataclass
class TitleIn:
    title: str
    locale: str | None
    kind: int  # models.NAME_*


@dataclass
class PersonIn:
    provider: str
    external_id: str
    name: str
    notability: int = 0
    id: uuid.UUID | None = None


@dataclass
class CreditIn:
    person: PersonIn
    department: str
    job: str
    character: str | None
    order: int


@dataclass
class AssetIn:
    kind: str
    url: str
    width: int | None
    height: int | None
    source: str
    source_kind: str
    attribution: str | None
    license: str | None = None
    source_url: str | None = None


@dataclass
class MovieIn:
    provider: str
    external_id: str
    canonical_title: str
    original_title: str | None = None
    original_language: str | None = None
    release_date: date | None = None
    release_year: int | None = None
    release_country: str | None = None
    runtime_minutes: int | None = None
    synopsis: str | None = None
    description: str | None = None
    status: str = "unknown"
    kind: str = "feature"
    notability: int = 0
    genres: list[str] = field(default_factory=list)
    titles: list[TitleIn] = field(default_factory=list)
    credits: list[CreditIn] = field(default_factory=list)
    assets: list[AssetIn] = field(default_factory=list)
    # Other providers' IDs for the same film (IMDb, TMDB, Wikipedia). Used for links, never to merge films.
    links: list[tuple[str, str]] = field(default_factory=list)
    # The fixture catalog carries its own UUIDs; other providers get stable_id().
    id: uuid.UUID | None = None
    payload: dict[str, Any] = field(default_factory=dict)


class Provider(Protocol):
    name: str

    def batches(self, checkpoint: dict[str, Any]) -> Iterator[tuple[list[MovieIn], dict[str, Any]]]:
        """Yields (records, checkpoint after this batch). Resuming with that checkpoint continues after it."""
        ...
