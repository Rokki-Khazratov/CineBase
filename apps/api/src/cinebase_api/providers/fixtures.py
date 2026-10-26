"""The hand-authored Phase 1 catalog (fixtures/), loaded the same way the web FixtureCatalog loads it."""

import json
import uuid
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import Any

from ..models import NAME_ALTERNATE
from .base import AssetIn, CreditIn, MovieIn, PersonIn, TitleIn

PROVIDER = "cinebase-fixture"
VERSION = "fixtures-2026-10-26"
POSTER_BASE_URL = "/fixture-art/"


def default_root() -> Path:
    return Path(__file__).resolve().parents[5] / "fixtures"


def _load(root: Path, name: str) -> Any:
    return json.loads((root / name).read_text(encoding="utf-8"))


def apply_import_batch(movies: list[dict[str, Any]], batch: dict[str, Any]) -> list[dict[str, Any]]:
    """Same merge as applyImportBatch in apps/web/src/catalog/fixture-data.ts."""
    by_external = {(e["provider"], e["external_id"]): i for i, m in enumerate(movies) for e in m["external_ids"]}
    merged = [{**m, "alternate_titles": list(m["alternate_titles"])} for m in movies]
    for record in batch["records"]:
        key = (record["external_id"]["provider"], record["external_id"]["external_id"])
        if key not in by_external:
            raise ValueError(f"Import batch references unknown external ID {key[0]}:{key[1]}")
        movie = merged[by_external[key]]
        if record.get("release_year") is not None and movie["release_year"] is None:
            movie["release_year"] = record["release_year"]
        if record.get("runtime_minutes") is not None:
            movie["runtime_minutes"] = record["runtime_minutes"]
        if record.get("synopsis") is not None:
            movie["synopsis"] = record["synopsis"]
        seen = {movie["title"], movie["original_title"], *(a["title"] for a in movie["alternate_titles"])}
        for alt in record.get("alternate_titles", []):
            if alt["title"] not in seen:
                movie["alternate_titles"].append(alt)
                seen.add(alt["title"])
    return merged


class FixtureProvider:
    name = PROVIDER

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or default_root()

    def genres(self) -> list[tuple[str, str]]:
        return [(g["slug"], g["name"]) for g in _load(self.root, "genres.json")]

    def collections(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = _load(self.root, "collections.json")
        return result

    def raw_movies(self) -> list[dict[str, Any]]:
        movies: list[dict[str, Any]] = _load(self.root, "movies.json")
        for path in sorted((self.root / "import-batches").glob("*.json")):
            movies = apply_import_batch(movies, json.loads(path.read_text(encoding="utf-8")))
        return movies

    def records(self) -> list[MovieIn]:
        people = {p["slug"]: p for p in _load(self.root, "people.json")}
        out = []
        for raw in self.raw_movies():
            primary = next(e for e in raw["external_ids"] if e["provider"] == PROVIDER)
            poster = raw["poster"]
            out.append(
                MovieIn(
                    provider=PROVIDER,
                    external_id=primary["external_id"],
                    id=uuid.UUID(raw["id"]),
                    canonical_title=raw["title"],
                    original_title=raw["original_title"],
                    original_language=raw["original_language"],
                    release_date=date.fromisoformat(raw["release_date"]) if raw["release_date"] else None,
                    release_year=raw["release_year"],
                    release_country=raw["release_country"],
                    runtime_minutes=raw["runtime_minutes"],
                    synopsis=raw["synopsis"],
                    status=raw["status"],
                    genres=list(raw["genres"]),
                    titles=[TitleIn(a["title"], a["locale"], NAME_ALTERNATE) for a in raw["alternate_titles"]],
                    credits=[
                        CreditIn(
                            person=PersonIn(
                                provider=PROVIDER,
                                external_id=c["person"],
                                name=people[c["person"]]["name"],
                                id=uuid.UUID(people[c["person"]]["id"]),
                            ),
                            department=c["department"],
                            job=c["job"],
                            character=c["character"],
                            order=c["order"],
                        )
                        for c in raw["credits"]
                    ],
                    assets=[
                        AssetIn(
                            kind="poster",
                            url=POSTER_BASE_URL + poster["file"],
                            width=400,
                            height=600,
                            source="CineBase generated art",
                            source_kind="synthetic",
                            attribution="Generated placeholder, not the film's official artwork",
                        )
                    ]
                    if poster
                    else [],
                    links=[(e["provider"], e["external_id"]) for e in raw["external_ids"] if e is not primary],
                    payload={"slug": raw["slug"]},
                )
            )
        return out

    def batches(self, checkpoint: dict[str, Any]) -> Iterator[tuple[list[MovieIn], dict[str, Any]]]:
        yield self.records(), {"done": True}
