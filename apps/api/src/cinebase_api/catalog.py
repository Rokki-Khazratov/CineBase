"""Read side of the catalog: search, browse, details. SQL is explicit so ranking and keyset rules are visible."""

import uuid
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

from sqlalchemy import text
from sqlalchemy.orm import Session

from . import schemas
from .errors import ApiError, not_found
from .normalize import normalize_text, parse_title_year
from .query import MovieQuery, SortKey, decode_cursor, encode_cursor

SUBSTRING_MIN_LENGTH = 3
FUZZY_MIN_LENGTH = 4
# pg_trgm strict word similarity: the query has to look like whole words of a title.
FUZZY_THRESHOLD = 0.5
# Lower bound on how many matching names are ranked for one query. Very short or very common queries can
# match hundreds of thousands of names; beyond the best candidates of each tier the order is not useful.
CANDIDATES_PER_TIER = 5000

PROVIDER_NAMES = {
    "cinebase-fixture": "CineBase fixtures",
    "wikidata": "Wikidata",
    "imdb": "IMDb",
    "tmdb": "TMDB",
    "enwiki": "Wikipedia",
}


def provider_url(provider: str, external_id: str) -> str | None:
    match provider:
        case "wikidata":
            return f"https://www.wikidata.org/wiki/{external_id}"
        case "imdb":
            return f"https://www.imdb.com/title/{external_id}/"
        case "tmdb":
            return f"https://www.themoviedb.org/movie/{external_id}"
        case "enwiki":
            return f"https://en.wikipedia.org/wiki/{quote(external_id.replace(' ', '_'))}"
    return None


def catalog_version(session: Session) -> str:
    value = session.execute(text("SELECT value FROM catalog_meta WHERE key = 'version'")).scalar()
    return value or "empty"


def catalog_info(session: Session) -> schemas.CatalogInfo:
    rows: dict[str, str] = dict(session.execute(text("SELECT key, value FROM catalog_meta")).all())
    count = rows.get("movie_count")
    return schemas.CatalogInfo(
        movie_count=int(count) if count else session.execute(text("SELECT count(*) FROM movie")).scalar_one(),
        catalog_version=rows.get("version", "empty"),
        sources=[s for s in rows.get("sources", "").split(",") if s],
    )


# --- search and browse -----------------------------------------------------------------------------


@dataclass
class SortPart:
    expr: str
    descending: bool
    is_uuid: bool = False


def _sort_parts(sort: str, wanted_year: int | None) -> list[SortPart]:
    year_null = SortPart("(m.release_year IS NULL)::int", False)
    title = SortPart("m.title_key", False)
    ident = SortPart("m.id", False, is_uuid=True)
    match sort:
        case "relevance":
            parts = []
            if wanted_year is not None:
                parts.append(SortPart(f"(m.release_year IS DISTINCT FROM {int(wanted_year)})::int", False))
            return [
                *parts,
                SortPart("h.tier", False),
                # Within a tier, a match on the display title beats an original or alternate title.
                SortPart("h.kind", False),
                # Among equally good matches, the film more people know comes first.
                SortPart("m.notability", True),
                SortPart("h.score", True),
                year_null,
                SortPart("coalesce(m.release_year, 0)", True),
                title,
                ident,
            ]
        case "notable":
            newest = SortPart("coalesce(m.release_year, 0)", True)
            return [SortPart("m.notability", True), year_null, newest, title, ident]
        case "title_asc":
            return [title, year_null, SortPart("coalesce(m.release_year, 0)", False), ident]
        case "release_desc" | "release_asc":
            # Full dates sort as YYYY-MM-DD, year-only as YYYY: in the same year, known days come first when
            # newest-first. Films without any date go last in both directions.
            return [
                SortPart("(m.release_key IS NULL)::int", False),
                SortPart("coalesce(m.release_key, '')", sort == "release_desc"),
                title,
                ident,
            ]
        case "runtime_asc" | "runtime_desc":
            return [
                SortPart("(m.runtime_minutes IS NULL)::int", False),
                SortPart("coalesce(m.runtime_minutes, 0)", sort == "runtime_desc"),
                title,
                ident,
            ]
    raise ValueError(sort)


def _keyset(parts: Sequence[SortPart], key: SortKey, params: dict[str, Any]) -> str:
    if len(key) != len(parts):
        raise ApiError(400, "invalid_cursor", "This page link is no longer valid. Start the list again.")
    ors = []
    for i in range(len(parts)):
        ands = []
        for j in range(i + 1):
            name = f"k{j}"
            value = key[j]
            if parts[j].is_uuid:
                try:
                    value = str(uuid.UUID(str(value)))
                except ValueError:
                    raise ApiError(400, "invalid_cursor", "This page link is no longer valid.") from None
            params[name] = value
            ref = f"CAST(:{name} AS uuid)" if parts[j].is_uuid else f":{name}"
            op = "=" if j < i else ("<" if parts[j].descending else ">")
            ands.append(f"{parts[j].expr} {op} {ref}")
        ors.append("(" + " AND ".join(ands) + ")")
    return "(" + " OR ".join(ors) + ")"


def _filters(query: MovieQuery, params: dict[str, Any]) -> list[str]:
    where = []
    if query.genres:
        params["genres"] = list(query.genres)
        where.append(
            "EXISTS (SELECT 1 FROM movie_genre mg JOIN genre g ON g.id = mg.genre_id "
            "WHERE mg.movie_id = m.id AND g.slug = ANY(:genres))"
        )
    if query.year_from is not None:
        params["year_from"] = query.year_from
        where.append("m.release_year >= :year_from")
    if query.year_to is not None:
        params["year_to"] = query.year_to
        where.append("m.release_year <= :year_to")
    if query.runtime_max is not None:
        params["runtime_max"] = query.runtime_max
        where.append("m.runtime_minutes <= :runtime_max")
    if "short" in query.exclude:
        where.append("m.kind <> 'short'")
    if "tv" in query.exclude:
        where.append("m.kind <> 'tv'")
    if "unreleased" in query.exclude:
        where.append("m.status <> 'announced'")
    if "documentary" in query.exclude:
        where.append(
            "NOT EXISTS (SELECT 1 FROM movie_genre mg JOIN genre g ON g.id = mg.genre_id "
            "WHERE mg.movie_id = m.id AND g.slug = 'documentary')"
        )
    return where


def _name_hits(normalized: str, params: dict[str, Any]) -> str:
    """Best match per film over all its names: tier (exact, prefix, word prefix, substring, similar), kind, score."""
    params["q"] = normalized
    params["q_prefix"] = normalized + "%"
    params["q_word"] = "% " + normalized + "%"
    params["q_sub"] = "%" + normalized + "%"
    params["per_tier"] = CANDIDATES_PER_TIER
    tiers = [
        "SELECT movie_id, 0 AS tier, name_kind, 1.0::float8 AS score FROM alternate_title WHERE normalized_title = :q",
        "SELECT movie_id, 1, name_kind, length(:q)::float8 / length(normalized_title) FROM alternate_title "
        "WHERE normalized_title LIKE :q_prefix AND normalized_title <> :q",
        "SELECT movie_id, 2, name_kind, length(:q)::float8 / length(normalized_title) FROM alternate_title "
        "WHERE normalized_title LIKE :q_word AND normalized_title NOT LIKE :q_prefix",
    ]
    if len(normalized) >= SUBSTRING_MIN_LENGTH:
        tiers.append(
            "SELECT movie_id, 3, name_kind, length(:q)::float8 / length(normalized_title) FROM alternate_title "
            "WHERE normalized_title LIKE :q_sub AND normalized_title NOT LIKE :q_prefix "
            "AND normalized_title NOT LIKE :q_word"
        )
    if len(normalized) >= FUZZY_MIN_LENGTH:
        tiers.append(
            "SELECT movie_id, 4, name_kind, strict_word_similarity(:q, normalized_title) FROM alternate_title "
            "WHERE :q <<% normalized_title AND normalized_title NOT LIKE :q_sub"
        )
    # Each tier keeps its best candidates (ORDER BY score, then the shortest names) so a one-letter query
    # cannot force a sort of every title in the catalog.
    limited = [
        f"(SELECT * FROM ({sql}) t{i} ORDER BY 4 DESC, 1 LIMIT :per_tier)" if i > 0 else f"({sql})"
        for i, sql in enumerate(tiers)
    ]
    union = " UNION ALL ".join(limited)
    return (
        "name_hits AS (SELECT DISTINCT ON (movie_id) movie_id, tier, name_kind AS kind, "
        f"round(score * 1e6)::int AS score FROM ({union}) u(movie_id, tier, name_kind, score) "
        "ORDER BY movie_id, tier, score DESC, name_kind)"
    )


def list_movies(session: Session, query: MovieQuery) -> schemas.MoviePage:
    version = catalog_version(session)
    params: dict[str, Any] = {}
    text_part, wanted_year = parse_title_year(query.q)
    normalized = normalize_text(text_part) if query.q else ""
    if query.q and not normalized:
        # Only punctuation: nothing can match, but the request is valid.
        return schemas.MoviePage(items=[], next_cursor=None, has_more=False, total=0)

    sort = query.sort
    if sort == "relevance" and not normalized:
        sort = "notable"
    parts = _sort_parts(sort, wanted_year if normalized else None)

    with_sql = ""
    join = ""
    if normalized:
        if len(normalized) >= FUZZY_MIN_LENGTH:
            session.execute(text(f"SET LOCAL pg_trgm.strict_word_similarity_threshold = {FUZZY_THRESHOLD}"))
        with_sql = "WITH " + _name_hits(normalized, params) + " "
        join = "JOIN name_hits h ON h.movie_id = m.id"

    where = _filters(query, params)
    base_where = list(where)
    if query.cursor:
        key = decode_cursor(query.cursor, query, version)
        where.append(_keyset(parts, key, params))

    select_keys = ", ".join(f"{p.expr} AS k{i}" for i, p in enumerate(parts))
    order = ", ".join(f"k{i} {'DESC' if p.descending else 'ASC'}" for i, p in enumerate(parts))
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    params["limit"] = query.limit + 1
    sql = f"{with_sql}SELECT m.id, {select_keys} FROM movie m {join} {where_sql} ORDER BY {order} LIMIT :limit"
    rows = session.execute(text(sql), params).all()

    has_more = len(rows) > query.limit
    rows = rows[: query.limit]
    ids = [row[0] for row in rows]
    summaries = load_summaries(session, ids)

    total: int | None = None
    if not query.cursor:
        count_where = ("WHERE " + " AND ".join(base_where)) if base_where else ""
        # No cursor on the first page, so params holds no keyset values.
        count_params = {k: v for k, v in params.items() if k != "limit"}
        count_sql = f"{with_sql}SELECT count(*) FROM movie m {join} {count_where}"
        total = session.execute(text(count_sql), count_params).scalar_one()

    next_cursor = None
    if has_more and rows:
        last = rows[-1]
        key_values: SortKey = [str(v) if isinstance(v, uuid.UUID) else v for v in last[1:]]
        next_cursor = encode_cursor(query, version, key_values)
    return schemas.MoviePage(
        items=[summaries[i] for i in ids if i in summaries], next_cursor=next_cursor, has_more=has_more, total=total
    )


# --- hydration -------------------------------------------------------------------------------------


def _media(row: Any, title: str, year: int | None) -> schemas.Media:
    synthetic = row.source_kind == "synthetic"
    label = f"{title} ({year})" if year else title
    return schemas.Media(
        url=row.url,
        alt=f"Illustrative poster for {label}" if synthetic else f"Poster for {label}",
        width=row.width,
        height=row.height,
        source=schemas.MediaSource(
            name=row.source,
            kind=row.source_kind,
            attribution=row.attribution,
            license=row.license,
            url=row.source_url,
        ),
    )


def load_summaries(session: Session, ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, schemas.MovieSummary]:
    if not ids:
        return {}
    params = {"ids": list(ids)}
    movies = session.execute(
        text(
            "SELECT id, canonical_title, original_title, release_year, runtime_minutes, kind "
            "FROM movie WHERE id = ANY(:ids)"
        ),
        params,
    ).all()
    genres: dict[uuid.UUID, list[schemas.GenreRef]] = defaultdict(list)
    for row in session.execute(
        text(
            "SELECT mg.movie_id, g.slug, g.name FROM movie_genre mg JOIN genre g ON g.id = mg.genre_id "
            "WHERE mg.movie_id = ANY(:ids) ORDER BY g.slug"
        ),
        params,
    ):
        genres[row.movie_id].append(schemas.GenreRef(slug=row.slug, name=row.name))
    directors: dict[uuid.UUID, list[schemas.PersonRef]] = defaultdict(list)
    for row in session.execute(
        text(
            "SELECT c.movie_id, p.id, p.name FROM credit c JOIN person p ON p.id = c.person_id "
            "WHERE c.movie_id = ANY(:ids) AND c.department = 'Directing' AND c.job = 'Director' ORDER BY c.ord, p.name"
        ),
        params,
    ):
        refs = directors[row.movie_id]
        if not any(r.id == str(row.id) for r in refs):
            refs.append(schemas.PersonRef(id=str(row.id), name=row.name))
    posters = {
        row.movie_id: row
        for row in session.execute(
            text(
                "SELECT DISTINCT ON (movie_id) movie_id, url, width, height, source, source_kind, attribution, "
                "license, source_url FROM movie_asset WHERE movie_id = ANY(:ids) AND kind = 'poster' "
                "ORDER BY movie_id, preferred DESC, id"
            ),
            params,
        )
    }
    out = {}
    for m in movies:
        poster = posters.get(m.id)
        out[m.id] = schemas.MovieSummary(
            id=str(m.id),
            title=m.canonical_title,
            original_title=m.original_title,
            year=m.release_year,
            runtime_minutes=m.runtime_minutes,
            poster=_media(poster, m.canonical_title, m.release_year) if poster else None,
            genres=genres[m.id],
            directors=directors[m.id],
            kind=m.kind,
        )
    return out


def _parse_uuid(value: str, code: str, message: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise not_found(code, message) from None


MOVIE_NOT_FOUND = ("movie_not_found", "No film with this ID exists in the catalog.")


def get_movie(session: Session, movie_id: str) -> schemas.MovieDetail:
    mid = _parse_uuid(movie_id, *MOVIE_NOT_FOUND)
    row = session.execute(
        text(
            "SELECT id, original_language, release_date, release_country, status, synopsis, description "
            "FROM movie WHERE id = :id"
        ),
        {"id": mid},
    ).one_or_none()
    if row is None:
        raise not_found(*MOVIE_NOT_FOUND)
    summary = load_summaries(session, [mid])[mid]
    titles = session.execute(
        text(
            "SELECT title, locale FROM alternate_title WHERE movie_id = :id AND name_kind = 2 "
            "ORDER BY locale NULLS LAST, title"
        ),
        {"id": mid},
    ).all()
    sources = session.execute(
        text(
            "SELECT provider, external_id FROM external_id WHERE movie_id = :id "
            "ORDER BY CASE provider WHEN 'wikidata' THEN 0 WHEN 'cinebase-fixture' THEN 0 WHEN 'enwiki' THEN 1 "
            "WHEN 'imdb' THEN 2 WHEN 'tmdb' THEN 3 ELSE 4 END, provider"
        ),
        {"id": mid},
    ).all()
    return schemas.MovieDetail(
        **summary.model_dump(),
        synopsis=row.synopsis,
        description=row.description,
        backdrop=None,
        original_language=row.original_language,
        release=schemas.Release(
            status=row.status,
            date=row.release_date.isoformat() if row.release_date else None,
            country=row.release_country,
        ),
        alternate_titles=[schemas.AlternateTitle(title=t.title, locale=t.locale) for t in titles],
        provenance=schemas.Provenance(
            sources=[
                schemas.ProvenanceSource(
                    name=PROVIDER_NAMES.get(s.provider, s.provider),
                    external_id=s.external_id,
                    url=provider_url(s.provider, s.external_id),
                )
                for s in sources
            ],
            catalog_version=catalog_version(session),
        ),
        links=schemas.MovieLinks(credits=f"/api/v1/movies/{mid}/credits"),
    )


def get_credits(session: Session, movie_id: str) -> schemas.MovieCredits:
    mid = _parse_uuid(movie_id, *MOVIE_NOT_FOUND)
    if session.execute(text("SELECT 1 FROM movie WHERE id = :id"), {"id": mid}).first() is None:
        raise not_found(*MOVIE_NOT_FOUND)
    rows = session.execute(
        text(
            "SELECT p.id, p.name, c.department, c.job, c.character, c.ord FROM credit c "
            "JOIN person p ON p.id = c.person_id WHERE c.movie_id = :id ORDER BY c.ord, p.name"
        ),
        {"id": mid},
    ).all()
    credits = [
        schemas.Credit(
            person=schemas.PersonRef(id=str(r.id), name=r.name),
            department=r.department,
            job=r.job,
            character=r.character,
            order=r.ord,
        )
        for r in rows
    ]
    return schemas.MovieCredits(
        movie_id=str(mid),
        cast=[c for c in credits if c.department == "Acting"],
        crew=[c for c in credits if c.department != "Acting"],
    )


def list_genres(session: Session) -> list[schemas.GenreRef]:
    rows = session.execute(text("SELECT slug, name FROM genre ORDER BY name")).all()
    return [schemas.GenreRef(slug=r.slug, name=r.name) for r in rows]


# --- collections and discover ----------------------------------------------------------------------


def list_collections(session: Session) -> list[schemas.Collection]:
    rows = session.execute(
        text(
            "SELECT c.slug, c.title, c.description, count(ci.id) AS n FROM collection c "
            "LEFT JOIN collection_item ci ON ci.collection_id = c.id GROUP BY c.id ORDER BY c.position, c.slug"
        )
    ).all()
    return [schemas.Collection(slug=r.slug, title=r.title, description=r.description, movie_count=r.n) for r in rows]


def get_collection(session: Session, slug: str) -> schemas.Collection:
    for c in list_collections(session):
        if c.slug == slug:
            return c
    raise not_found("collection_not_found", "No collection with this slug exists.")


def collection_movies(session: Session, slug: str) -> schemas.MoviePage:
    get_collection(session, slug)
    ids = list(
        session.execute(
            text(
                "SELECT ci.movie_id FROM collection_item ci JOIN collection c ON c.id = ci.collection_id "
                "WHERE c.slug = :slug ORDER BY ci.position"
            ),
            {"slug": slug},
        ).scalars()
    )
    summaries = load_summaries(session, ids)
    items = [summaries[i] for i in ids if i in summaries]
    return schemas.MoviePage(items=items, next_cursor=None, has_more=False, total=len(items))


def discover(session: Session) -> schemas.Discover:
    blocks = []
    for c in list_collections(session):
        if c.movie_count == 0:
            continue
        blocks.append(schemas.DiscoverBlock(**c.model_dump(), items=collection_movies(session, c.slug).items))
    return schemas.Discover(blocks=blocks, catalog=catalog_info(session))


# --- people ----------------------------------------------------------------------------------------

PERSON_NOT_FOUND = ("person_not_found", "No person with this ID exists in the catalog.")


def get_person(session: Session, person_id: str) -> schemas.Person:
    pid = _parse_uuid(person_id, *PERSON_NOT_FOUND)
    row = session.execute(
        text("SELECT id, name, provider, external_id FROM person WHERE id = :id"), {"id": pid}
    ).one_or_none()
    if row is None:
        raise not_found(*PERSON_NOT_FOUND)
    sources = []
    if row.provider != "cinebase-fixture":
        url = f"https://www.wikidata.org/wiki/{row.external_id}" if row.provider == "wikidata" else None
        sources.append(
            schemas.ProvenanceSource(
                name=PROVIDER_NAMES.get(row.provider, row.provider), external_id=row.external_id, url=url
            )
        )
    return schemas.Person(id=str(row.id), name=row.name, sources=sources)


def person_movies(session: Session, person_id: str, limit: int, cursor: str | None) -> schemas.PersonMoviePage:
    person = get_person(session, person_id)
    version = catalog_version(session)
    fake_query = MovieQuery(q=f"person:{person.id}", sort="release_desc", limit=limit)
    parts = [
        SortPart("(m.release_key IS NULL)::int", False),
        SortPart("coalesce(m.release_key, '')", True),
        SortPart("m.title_key", False),
        SortPart("m.id", False, is_uuid=True),
        SortPart("c.id", False),
    ]
    params: dict[str, Any] = {"pid": uuid.UUID(person.id), "limit": limit + 1}
    where = ["c.person_id = :pid"]
    if cursor:
        where.append(_keyset(parts, decode_cursor(cursor, fake_query, version), params))
    select_keys = ", ".join(f"{p.expr} AS k{i}" for i, p in enumerate(parts))
    order = ", ".join(f"k{i} {'DESC' if p.descending else 'ASC'}" for i, p in enumerate(parts))
    rows = session.execute(
        text(
            f"SELECT m.id, c.department, c.job, c.character, {select_keys} FROM credit c "
            f"JOIN movie m ON m.id = c.movie_id WHERE {' AND '.join(where)} ORDER BY {order} LIMIT :limit"
        ),
        params,
    ).all()
    has_more = len(rows) > limit
    rows = rows[:limit]
    summaries = load_summaries(session, [r.id for r in rows])
    next_cursor = None
    if has_more and rows:
        last = rows[-1]
        next_cursor = encode_cursor(fake_query, version, [str(v) if isinstance(v, uuid.UUID) else v for v in last[4:]])
    return schemas.PersonMoviePage(
        items=[
            schemas.PersonMovie(movie=summaries[r.id], department=r.department, job=r.job, character=r.character)
            for r in rows
            if r.id in summaries
        ],
        next_cursor=next_cursor,
        has_more=has_more,
    )
