"""cinebase CLI: migrate, seed-fixtures, import wikidata [--resume], link-collections."""

import argparse
import json
import logging
import shutil
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from . import importer
from .db import get_engine, session_factory
from .normalize import normalize_text
from .providers import fixtures, wikidata
from .providers.base import Provider
from .settings import get_settings

log = logging.getLogger("cinebase.cli")
API_ROOT = Path(__file__).resolve().parents[2]
# The import stops (resumably) before the database can fill the disk.
MIN_FREE_DISK = 1_500_000_000


def migrate(url: str) -> None:
    config = Config(str(API_ROOT / "alembic.ini"))
    config.attributes["database_url"] = url
    command.upgrade(config, "head")


def seed_fixtures(engine: Engine, root: Path | None = None) -> importer.ImportReport:
    """Loads the Phase 1 fixture catalog. Idempotent: films keep their UUIDs and nothing is duplicated."""
    provider = fixtures.FixtureProvider(root)
    with session_factory(engine).begin() as session:
        genre_ids = importer.ensure_genres(session, provider.genres())
        report = importer.upsert_movies(session, provider.records(), genre_ids)
        by_slug = {r.payload["slug"]: r.id for r in provider.records() if r.id is not None and "slug" in r.payload}
        _write_collections(session, provider.collections(), lambda slug: by_slug.get(slug))
        importer.finish_catalog(session, fixtures.VERSION, [fixtures.PROVIDER])
    return report


def _write_collections(session: Session, collections: list[dict[str, Any]], resolve: Any) -> list[str]:
    """Replaces editorial collections. Returns the fixture slugs that could not be resolved to a film."""
    missing: list[str] = []
    session.execute(text("DELETE FROM collection"))
    for position, c in enumerate(collections):
        collection_id = session.execute(
            text("INSERT INTO collection (slug, title, description, position) VALUES (:s, :t, :d, :p) RETURNING id"),
            {"s": c["slug"], "t": c["title"], "d": c["description"], "p": position},
        ).scalar_one()
        seen = set()
        for i, slug in enumerate(c["movies"]):
            movie_id = resolve(slug)
            if movie_id is None:
                missing.append(slug)
                continue
            if movie_id in seen:
                continue
            seen.add(movie_id)
            session.execute(
                text("INSERT INTO collection_item (collection_id, movie_id, position) VALUES (:c, :m, :p)"),
                {"c": collection_id, "m": movie_id, "p": i},
            )
    return missing


def link_collections(engine: Engine, root: Path | None = None) -> list[str]:
    """Points the editorial collections at the best-known catalog film with the same title and year.

    Used for a Wikidata catalog, where the fixture UUIDs do not exist.
    """
    provider = fixtures.FixtureProvider(root)
    films = {m["slug"]: m for m in provider.raw_movies()}
    with session_factory(engine).begin() as session:

        def resolve(slug: str) -> Any:
            film = films.get(slug)
            if film is None:
                return None
            names = [normalize_text(n) for n in (film["title"], film["original_title"]) if n]
            return session.execute(
                text(
                    "SELECT m.id FROM movie m JOIN alternate_title a ON a.movie_id = m.id "
                    "WHERE a.normalized_title = ANY(:n) AND a.name_kind < 2 "
                    "AND (m.release_year = :y OR CAST(:y AS int) IS NULL) "
                    "ORDER BY m.notability DESC, m.id LIMIT 1"
                ),
                {"n": names, "y": film["release_year"]},
            ).scalar()

        missing = _write_collections(session, provider.collections(), resolve)
    return missing


def run_import(engine: Engine, provider: Provider, resume: bool, genres: list[tuple[str, str]]) -> int:
    """Runs a provider import batch by batch. Each batch commits with the checkpoint that follows it."""
    factory = session_factory(engine)
    with factory.begin() as session:
        genre_ids = importer.ensure_genres(session, genres)
        previous = None
        if resume:
            previous = session.execute(
                text(
                    "SELECT id, checkpoint FROM import_run WHERE provider = :p AND status IN ('failed', 'running') "
                    "ORDER BY id DESC LIMIT 1"
                ),
                {"p": provider.name},
            ).one_or_none()
            if previous is None:
                log.info("nothing to resume for %s, starting a new run", provider.name)
        if previous is not None:
            run_id, checkpoint = previous.id, dict(previous.checkpoint)
            session.execute(
                text("UPDATE import_run SET status = 'running', error = NULL WHERE id = :id"), {"id": run_id}
            )
            log.info("resuming run %s after %s", run_id, checkpoint.get("after_qid", "start"))
        else:
            checkpoint = {}
            run_id = session.execute(
                text("INSERT INTO import_run (provider, status) VALUES (:p, 'running') RETURNING id"),
                {"p": provider.name},
            ).scalar_one()

    total = importer.ImportReport()
    started = time.monotonic()
    try:
        for records, next_checkpoint in provider.batches(checkpoint):
            free = shutil.disk_usage("/").free
            if free < MIN_FREE_DISK:
                raise RuntimeError(f"only {free / 1e9:.1f} GB of disk left; free some space and resume")
            with factory.begin() as session:
                report = importer.upsert_movies(session, records, genre_ids)
                session.execute(
                    text(
                        "UPDATE import_run SET imported = imported + :i, updated = updated + :u, "
                        "failed = failed + :f, checkpoint = CAST(:c AS jsonb) WHERE id = :id"
                    ),
                    {
                        "i": report.imported,
                        "u": report.updated,
                        "f": report.failed,
                        "c": _json(next_checkpoint),
                        "id": run_id,
                    },
                )
            total.add(report)
            for error in report.errors[:5]:
                log.warning("skipped %s", error)
            done, of = next_checkpoint.get("seen"), next_checkpoint.get("total")
            log.info(
                "run %s: +%d new, +%d updated, %d skipped (%s/%s items, %.0fs)",
                run_id,
                report.imported,
                report.updated,
                report.failed,
                done,
                of,
                time.monotonic() - started,
            )
    except (Exception, KeyboardInterrupt) as exc:
        with factory.begin() as session:
            session.execute(
                text("UPDATE import_run SET status = 'failed', error = :e WHERE id = :id"),
                {"e": f"{type(exc).__name__}: {exc}"[:2000], "id": run_id},
            )
        log.error("import stopped: %s. Run again with --resume to continue.", exc)
        return 1

    with factory.begin() as session:
        version = f"{provider.name}-{datetime.now(UTC):%Y%m%d}-run{run_id}"
        sources = session.execute(text("SELECT DISTINCT provider FROM import_run WHERE status <> 'failed'")).scalars()
        importer.finish_catalog(session, version, sorted(set(sources) | {provider.name}))
        session.execute(
            text("UPDATE import_run SET status = 'completed', finished_at = now() WHERE id = :id"), {"id": run_id}
        )
        row = session.execute(
            text("SELECT imported, updated, failed FROM import_run WHERE id = :id"), {"id": run_id}
        ).one()
    print(f"run {run_id} completed: {row.imported} imported, {row.updated} updated, {row.failed} failed")
    return 0


def _json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"))


def wikidata_provider(batch_size: int, limit: int | None) -> wikidata.WikidataProvider:
    settings = get_settings()
    client = httpx.Client(
        headers={"User-Agent": settings.wikidata_user_agent},
        timeout=httpx.Timeout(90.0, connect=15.0),
        follow_redirects=True,
    )
    wd = wikidata.WikidataClient(client, settings.wikidata_sparql_url, settings.commons_api_url)
    return wikidata.WikidataProvider(wd, batch_size=batch_size, limit=limit)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cinebase", description="CineBase catalog administration")
    parser.add_argument("--database-url", help="Overrides CINEBASE_DATABASE_URL")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("migrate", help="Apply database migrations")
    seed = sub.add_parser("seed-fixtures", help="Load the 43-film fixture catalog (idempotent)")
    seed.add_argument("--fixtures", type=Path, help="Path to the fixtures directory")
    imp = sub.add_parser("import", help="Import from a provider")
    imp.add_argument("provider", choices=["wikidata"])
    imp.add_argument("--resume", action="store_true", help="Continue the last failed or interrupted run")
    imp.add_argument("--batch-size", type=int, default=1000)
    imp.add_argument("--limit", type=int, help="Stop after this many listed items (for trials)")
    link = sub.add_parser("link-collections", help="Point editorial collections at catalog films by title and year")
    link.add_argument("--fixtures", type=Path)
    args = parser.parse_args(argv)

    logging.basicConfig(level=get_settings().log_level, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    url = args.database_url or get_settings().database_url
    engine = get_engine(url)

    if args.command == "migrate":
        migrate(url)
        print("database is at the latest schema")
        return 0
    if args.command == "seed-fixtures":
        report = seed_fixtures(engine, args.fixtures)
        print(f"fixtures: {report.imported} imported, {report.updated} updated, {report.failed} failed")
        return 1 if report.failed else 0
    if args.command == "import":
        provider = wikidata_provider(args.batch_size, args.limit)
        genres = [(slug, wikidata.GENRE_NAMES[slug]) for slug in wikidata.GENRES]
        return run_import(engine, provider, args.resume, genres)
    if args.command == "link-collections":
        missing = link_collections(engine, args.fixtures)
        print(f"collections linked; {len(missing)} films not found: {', '.join(missing) or 'none'}")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
