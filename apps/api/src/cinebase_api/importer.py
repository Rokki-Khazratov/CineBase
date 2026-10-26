"""Writes provider records into the catalog in set-based batches.

A film is identified by (provider, external_id). Re-importing it updates the same row and keeps its UUID;
everything the provider owns (names, genres, credits, assets from that source) is replaced, so a re-run
converges to the provider's current data instead of accumulating duplicates.
"""

import json
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from .models import NAME_ORIGINAL, NAME_TITLE
from .normalize import normalize_text
from .providers.base import MovieIn, stable_id


@dataclass
class ImportReport:
    imported: int = 0
    updated: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)

    def add(self, other: "ImportReport") -> None:
        self.imported += other.imported
        self.updated += other.updated
        self.failed += other.failed
        self.errors.extend(other.errors[: max(0, 50 - len(self.errors))])


def _validate(m: MovieIn) -> str | None:
    if not m.canonical_title.strip() or not normalize_text(m.canonical_title):
        return "missing title"
    if m.status not in ("released", "announced", "unknown"):
        return f"bad status {m.status}"
    if m.kind not in ("feature", "short", "tv"):
        return f"bad kind {m.kind}"
    if m.runtime_minutes is not None and not 0 < m.runtime_minutes < 32767:
        return f"bad runtime {m.runtime_minutes}"
    if m.release_year is not None and not 1850 <= m.release_year <= 2200:
        return f"bad year {m.release_year}"
    return None


def _release_key(m: MovieIn) -> str | None:
    if m.release_date:
        return m.release_date.isoformat()
    return f"{m.release_year:04d}" if m.release_year is not None else None


def _names(m: MovieIn) -> list[tuple[str, str, str | None, int]]:
    """(title, normalized, locale, kind), one per distinct normalized name, best kind first."""
    candidates: list[tuple[str, str | None, int]] = [(m.canonical_title, None, NAME_TITLE)]
    if m.original_title:
        candidates.append((m.original_title, m.original_language, NAME_ORIGINAL))
    candidates += [(t.title, t.locale, t.kind) for t in m.titles]
    seen: dict[str, tuple[str, str, str | None, int]] = {}
    for title, locale, kind in sorted(candidates, key=lambda c: c[2]):
        norm = normalize_text(title)
        if norm and norm not in seen:
            seen[norm] = (title.strip(), norm, locale, kind)
    return list(seen.values())


def upsert_movies(
    session: Session, records: Sequence[MovieIn], genre_ids: dict[str, int] | None = None
) -> ImportReport:
    """Upserts one batch inside the caller's transaction. Invalid records are counted and skipped."""
    report = ImportReport()
    valid: list[MovieIn] = []
    for r in records:
        problem = _validate(r)
        if problem:
            report.failed += 1
            report.errors.append(f"{r.provider}:{r.external_id}: {problem}")
        else:
            valid.append(r)
    if not valid:
        return report
    if genre_ids is None:
        genre_ids = dict(session.execute(text("SELECT slug, id FROM genre")).all())

    # Existing films keep their UUID, whatever provider created them.
    existing: dict[tuple[str, str], uuid.UUID] = {}
    for provider in {r.provider for r in valid}:
        ext = [r.external_id for r in valid if r.provider == provider]
        for row in session.execute(
            text("SELECT external_id, movie_id FROM external_id WHERE provider = :p AND external_id = ANY(:e)"),
            {"p": provider, "e": ext},
        ):
            existing[(provider, row.external_id)] = row.movie_id

    ids: dict[int, uuid.UUID] = {}
    by_id: dict[uuid.UUID, MovieIn] = {}
    for r in valid:
        mid = existing.get((r.provider, r.external_id)) or r.id or stable_id(r.provider, r.external_id)
        if mid in by_id:
            report.failed += 1
            report.errors.append(f"{r.provider}:{r.external_id}: duplicate in batch")
            continue
        ids[id(r)] = mid
        by_id[mid] = r
        if (r.provider, r.external_id) in existing:
            report.updated += 1
        else:
            report.imported += 1
    movie_ids = list(by_id)

    session.execute(
        text(
            "INSERT INTO movie (id, canonical_title, original_title, original_language, release_date, release_year, "
            "release_country, runtime_minutes, synopsis, description, status, kind, notability, title_key, "
            "release_key) VALUES (:id, :canonical_title, :original_title, :original_language, :release_date, "
            ":release_year, :release_country, :runtime_minutes, :synopsis, :description, :status, :kind, "
            ":notability, :title_key, :release_key) "
            "ON CONFLICT (id) DO UPDATE SET canonical_title = EXCLUDED.canonical_title, "
            "original_title = EXCLUDED.original_title, original_language = EXCLUDED.original_language, "
            "release_date = EXCLUDED.release_date, release_year = EXCLUDED.release_year, "
            "release_country = EXCLUDED.release_country, runtime_minutes = EXCLUDED.runtime_minutes, "
            "synopsis = coalesce(EXCLUDED.synopsis, movie.synopsis), description = EXCLUDED.description, "
            "status = EXCLUDED.status, kind = EXCLUDED.kind, notability = EXCLUDED.notability, "
            "title_key = EXCLUDED.title_key, release_key = EXCLUDED.release_key, updated_at = now()"
        ),
        [
            {
                "id": mid,
                "canonical_title": r.canonical_title.strip(),
                "original_title": r.original_title,
                "original_language": r.original_language,
                "release_date": r.release_date,
                "release_year": r.release_year,
                "release_country": r.release_country,
                "runtime_minutes": r.runtime_minutes,
                "synopsis": r.synopsis,
                "description": r.description,
                "status": r.status,
                "kind": r.kind,
                "notability": r.notability,
                "title_key": normalize_text(r.canonical_title),
                "release_key": _release_key(r),
            }
            for mid, r in by_id.items()
        ],
    )

    ext_rows = []
    for mid, r in by_id.items():
        ext_rows.append({"m": mid, "p": r.provider, "e": r.external_id})
        ext_rows += [{"m": mid, "p": p, "e": e} for p, e in r.links]
    # Secondary IDs can collide (two Wikidata items for one IMDb title); the first film keeps the link.
    session.execute(
        text(
            "INSERT INTO external_id (movie_id, provider, external_id) VALUES (:m, :p, :e) "
            "ON CONFLICT (provider, external_id) DO NOTHING"
        ),
        ext_rows,
    )

    sources = sorted({r.provider for r in valid})
    session.execute(
        text("DELETE FROM alternate_title WHERE movie_id = ANY(:ids) AND source = ANY(:s)"),
        {"ids": movie_ids, "s": sources},
    )
    title_rows = [
        {"m": mid, "t": t, "n": n, "l": loc, "s": r.provider, "k": k}
        for mid, r in by_id.items()
        for t, n, loc, k in _names(r)
    ]
    if title_rows:
        session.execute(
            text(
                "INSERT INTO alternate_title (movie_id, title, normalized_title, locale, source, name_kind) "
                "VALUES (:m, :t, :n, :l, :s, :k) ON CONFLICT (movie_id, normalized_title) DO UPDATE "
                "SET name_kind = least(alternate_title.name_kind, EXCLUDED.name_kind)"
            ),
            title_rows,
        )

    session.execute(text("DELETE FROM movie_genre WHERE movie_id = ANY(:ids)"), {"ids": movie_ids})
    genre_rows = [
        {"m": mid, "g": genre_ids[g]} for mid, r in by_id.items() for g in dict.fromkeys(r.genres) if g in genre_ids
    ]
    if genre_rows:
        session.execute(text("INSERT INTO movie_genre (movie_id, genre_id) VALUES (:m, :g)"), genre_rows)

    people: dict[tuple[str, str], dict[str, Any]] = {}
    for r in by_id.values():
        for c in r.credits:
            p = c.person
            key = (p.provider, p.external_id)
            pid = p.id or stable_id(p.provider, p.external_id)
            people[key] = {"id": pid, "name": p.name, "p": p.provider, "e": p.external_id, "n": p.notability}
    person_ids: dict[tuple[str, str], uuid.UUID] = {}
    if people:
        rows = session.execute(
            text(
                "INSERT INTO person (id, name, provider, external_id, notability) "
                "SELECT * FROM unnest(CAST(:id AS uuid[]), CAST(:name AS text[]), CAST(:p AS text[]), "
                "CAST(:e AS text[]), CAST(:n AS int[])) "
                "ON CONFLICT (provider, external_id) DO UPDATE SET name = EXCLUDED.name, "
                "notability = EXCLUDED.notability, updated_at = now() RETURNING id, provider, external_id"
            ),
            {
                "id": [v["id"] for v in people.values()],
                "name": [v["name"] for v in people.values()],
                "p": [v["p"] for v in people.values()],
                "e": [v["e"] for v in people.values()],
                "n": [v["n"] for v in people.values()],
            },
        )
        person_ids = {(row.provider, row.external_id): row.id for row in rows}

    session.execute(text("DELETE FROM credit WHERE movie_id = ANY(:ids)"), {"ids": movie_ids})
    credit_rows = [
        {
            "m": mid,
            "p": person_ids[(c.person.provider, c.person.external_id)],
            "d": c.department,
            "j": c.job,
            "c": c.character,
            "o": c.order,
        }
        for mid, r in by_id.items()
        for c in r.credits
    ]
    if credit_rows:
        session.execute(
            text(
                "INSERT INTO credit (movie_id, person_id, department, job, character, ord) "
                "VALUES (:m, :p, :d, :j, :c, :o)"
            ),
            credit_rows,
        )

    session.execute(
        text("DELETE FROM movie_asset WHERE movie_id = ANY(:ids) AND source = ANY(:s)"),
        {"ids": movie_ids, "s": sorted({a.source for r in valid for a in r.assets} | set(sources))},
    )
    asset_rows = [
        {
            "m": mid,
            "k": a.kind,
            "u": a.url,
            "w": a.width,
            "h": a.height,
            "s": a.source,
            "sk": a.source_kind,
            "a": a.attribution,
            "l": a.license,
            "su": a.source_url,
            "pref": i == 0,
        }
        for mid, r in by_id.items()
        for i, a in enumerate(r.assets)
    ]
    if asset_rows:
        session.execute(
            text(
                "INSERT INTO movie_asset (movie_id, kind, url, width, height, source, source_kind, attribution, "
                "license, source_url, preferred) VALUES (:m, :k, :u, :w, :h, :s, :sk, :a, :l, :su, :pref)"
            ),
            asset_rows,
        )

    snapshots = [
        {"m": mid, "p": r.provider, "f": datetime.now(UTC), "payload": json.dumps(r.payload, default=str)}
        for mid, r in by_id.items()
        if r.payload
    ]
    if snapshots:
        session.execute(
            text(
                "INSERT INTO provider_snapshot (movie_id, provider, fetched_at, payload) "
                "VALUES (:m, :p, :f, CAST(:payload AS jsonb)) ON CONFLICT (movie_id, provider) "
                "DO UPDATE SET fetched_at = EXCLUDED.fetched_at, payload = EXCLUDED.payload"
            ),
            snapshots,
        )
    return report


def ensure_genres(session: Session, genres: Sequence[tuple[str, str]]) -> dict[str, int]:
    for slug, name in genres:
        session.execute(
            text(
                "INSERT INTO genre (slug, name) VALUES (:s, :n) ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name"
            ),
            {"s": slug, "n": name},
        )
    return dict(session.execute(text("SELECT slug, id FROM genre")).all())


def finish_catalog(session: Session, version: str, sources: Sequence[str]) -> None:
    """Records the catalog version (it invalidates old cursors) and the cached film count."""
    count = session.execute(text("SELECT count(*) FROM movie")).scalar_one()
    for key, value in (("version", version), ("movie_count", str(count)), ("sources", ",".join(sources))):
        session.execute(
            text(
                "INSERT INTO catalog_meta (key, value) VALUES (:k, :v) "
                "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
            ),
            {"k": key, "v": value},
        )
