"""Public DTOs. They match apps/web/src/catalog/types.ts; the web client is generated from this OpenAPI schema."""

from typing import Literal

from pydantic import BaseModel, Field

SourceKind = Literal["synthetic", "provider", "local"]
ReleaseStatus = Literal["released", "announced", "unknown"]
MovieKind = Literal["feature", "short", "tv"]
Sort = Literal["relevance", "notable", "title_asc", "release_desc", "release_asc", "runtime_asc", "runtime_desc"]
Exclusion = Literal["short", "tv", "documentary", "unreleased"]

SORTS: tuple[str, ...] = Sort.__args__  # type: ignore[attr-defined]
EXCLUSIONS: tuple[str, ...] = Exclusion.__args__  # type: ignore[attr-defined]


class MediaSource(BaseModel):
    name: str
    kind: SourceKind
    attribution: str | None
    license: str | None = None
    # Page describing the file and its license, when the source has one.
    url: str | None = None


class Media(BaseModel):
    url: str
    alt: str
    width: int | None
    height: int | None
    source: MediaSource


class GenreRef(BaseModel):
    slug: str
    name: str


class PersonRef(BaseModel):
    id: str
    name: str


class MovieSummary(BaseModel):
    id: str
    title: str
    original_title: str | None
    year: int | None
    runtime_minutes: int | None
    poster: Media | None
    genres: list[GenreRef]
    directors: list[PersonRef]
    kind: MovieKind = "feature"


class AlternateTitle(BaseModel):
    title: str
    locale: str | None


class Release(BaseModel):
    status: ReleaseStatus
    date: str | None = Field(description="ISO date (YYYY-MM-DD), or null when the day is not known.")
    country: str | None


class ProvenanceSource(BaseModel):
    name: str
    external_id: str
    url: str | None = None


class Provenance(BaseModel):
    sources: list[ProvenanceSource]
    catalog_version: str


class MovieLinks(BaseModel):
    credits: str


class MovieDetail(MovieSummary):
    synopsis: str | None
    description: str | None = None
    backdrop: Media | None
    original_language: str | None
    release: Release
    alternate_titles: list[AlternateTitle]
    provenance: Provenance
    links: MovieLinks


class Credit(BaseModel):
    person: PersonRef
    department: str
    job: str
    character: str | None
    order: int


class MovieCredits(BaseModel):
    movie_id: str
    cast: list[Credit]
    crew: list[Credit]


class MoviePage(BaseModel):
    items: list[MovieSummary]
    next_cursor: str | None
    has_more: bool
    total: int | None = Field(default=None, description="Matching films; only computed for the first page.")


class Collection(BaseModel):
    slug: str
    title: str
    description: str
    movie_count: int


class DiscoverBlock(Collection):
    items: list[MovieSummary]


class CatalogInfo(BaseModel):
    movie_count: int
    catalog_version: str
    sources: list[str] = []


class Discover(BaseModel):
    blocks: list[DiscoverBlock]
    catalog: CatalogInfo


class Person(BaseModel):
    id: str
    name: str
    sources: list[ProvenanceSource]


class PersonMovie(BaseModel):
    movie: MovieSummary
    department: str
    job: str
    character: str | None


class PersonMoviePage(BaseModel):
    items: list[PersonMovie]
    next_cursor: str | None
    has_more: bool


class ErrorDetail(BaseModel):
    code: str
    message: str
    fields: dict[str, str] | None = None
    request_id: str


class ErrorBody(BaseModel):
    error: ErrorDetail


class Health(BaseModel):
    status: Literal["ok"]
