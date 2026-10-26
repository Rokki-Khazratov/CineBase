"""Importer behaviour against a fake Wikidata (httpx.MockTransport): mapping, idempotency, failure and resume."""

import re
from collections.abc import Iterator
from datetime import date
from typing import Any
from urllib.parse import parse_qs

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from cinebase_api import cli, importer
from cinebase_api.providers import fixtures, wikidata
from cinebase_api.providers.base import MovieIn

E = wikidata.ENTITY


def uri(qid: str) -> dict[str, str]:
    return {"type": "uri", "value": E + qid}


def lit(value: Any, lang: str | None = None) -> dict[str, str]:
    out = {"type": "literal", "value": str(value)}
    if lang:
        out["xml:lang"] = lang
    return out


RANK = "http://wikiba.se/ontology#NormalRank"
PREFERRED = "http://wikiba.se/ontology#PreferredRank"

# A tiny Wikidata: QID -> facts. Genre classes: Q130232 drama, Q9999 "psychological drama" (subclass of drama).
FILMS: dict[str, dict[str, Any]] = {
    "Q101": {
        "type": ["Q11424"],
        "genre": ["Q9999"],
        "lang": ["ru"],
        "country": ["SU"],
        "label": {"en": "Stalker", "ru": "Сталкер", "de": "Stalker"},
        "title": [("Сталкер", "ru")],
        "alias": ["Stalker (1979 film)"],
        "sl": 80,
        "desc": "1979 film by Andrei Tarkovsky",
        "enwiki": "Stalker (1979 film)",
        "imdb": "tt0079944",
        "tmdb": "1398",
        "poster": "http://commons.wikimedia.org/wiki/Special:FilePath/Stalker%20poster.jpg",
        "dates": [("+1979-05-25T00:00:00Z", 11, "SU"), ("+1980-01-01T00:00:00Z", 9, None)],
        "runtime": [("161", "Q7727", RANK), ("2.7", "Q25235", PREFERRED)],
        "credits": [("director", "Q201", None, None), ("cast", "Q202", None, "Stalker"), ("cast", "Q203", "1", None)],
    },
    "Q102": {
        "type": ["Q24862"],
        "label": {"mul": "La Jetée"},
        "sl": 30,
        "dates": [("+1962-01-01T00:00:00Z", 9, None)],
        "runtime": [("28", "Q7727", RANK)],
        "credits": [("director", "Q204", None, None)],
    },
    "Q103": {"type": ["Q11424", "Q506240"], "label": {"fr": "Un téléfilm"}, "sl": 1},
    "Q104": {"type": ["Q11424"], "genre": ["Q185529"], "label": {"en": "Adult film"}, "sl": 2},
    "Q105": {
        "type": ["Q11424"],
        "label": {"en": "Future Film"},
        "sl": 3,
        "dates": [("+2031-03-01T00:00:00Z", 11, None)],
    },
    "Q106": {"type": ["Q11424"], "label": {"en": "Sixth"}, "sl": 0},
    "Q107": {"type": ["Q11424"], "label": {"en": "Seventh"}, "sl": 0},
}
PEOPLE = {
    "Q201": ("Andrei Tarkovsky", 90),
    "Q202": ("Alexander Kaidanovsky", 20),
    "Q203": ("Anatoly Solonitsyn", 10),
    "Q204": ("Chris Marker", 40),
}
SUBCLASSES = {"Q130232": ["Q9999"]}


def _values(query: str) -> list[str]:
    match = re.search(r"VALUES \?[fp] \{([^}]*)\}", query)
    assert match, query
    return [v.removeprefix("wd:") for v in match.group(1).split()]


class FakeWikidata:
    def __init__(self) -> None:
        self.fail: dict[str, int] = {}  # query kind -> remaining failures
        self.fail_status = 400
        self.fail_headers: dict[str, str] = {}
        self.fail_on: tuple[str, int] | None = None  # (query kind, nth call) answered with HTTP 400
        self.calls: list[str] = []

    def kind(self, query: str) -> str:
        if "wdt:P279*" in query:
            return "subclass"
        if re.match(r"SELECT \?f WHERE \{ \?f wdt:P31 wd:", query):
            return "listing"
        if 'BIND("type"' in query:
            return "facts"
        if 'BIND("date"' in query:
            return "dates"
        if '("director" p:P57' in query:
            return "credits"
        return "people"

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if request.url.host == "commons.wikimedia.org":
            return self.commons(request)
        query = parse_qs(request.content.decode())["query"][0]
        kind = self.kind(query)
        self.calls.append(kind)
        if self.fail_on == (kind, self.calls.count(kind)):
            return httpx.Response(400, text="bad request")
        if self.fail.get(kind, 0) > 0:
            self.fail[kind] -= 1
            return httpx.Response(self.fail_status, headers=self.fail_headers, text="nope")
        rows = getattr(self, kind)(query)
        return httpx.Response(200, json={"results": {"bindings": rows}})

    def subclass(self, query: str) -> list[dict[str, Any]]:
        roots = re.findall(r"wd:(Q\d+)", query)
        return [{"c": uri(c)} for r in roots for c in [r, *SUBCLASSES.get(r, [])]]

    def listing(self, query: str) -> list[dict[str, Any]]:
        root = re.findall(r"wd:(Q\d+)", query)[0]
        return [{"f": uri(q)} for q, f in FILMS.items() if root in f["type"]]

    def facts(self, query: str) -> list[dict[str, Any]]:
        rows = []
        for q in _values(query):
            f = FILMS.get(q)
            if not f:
                continue

            def add(k: str, v: dict[str, str], q: str = q) -> None:
                rows.append({"f": uri(q), "k": lit(k), "v": v})

            for t in f["type"]:
                add("type", uri(t))
            for g in f.get("genre", []):
                add("genre", uri(g))
            for code in f.get("lang", []):
                add("lang", lit(code))
            for code in f.get("country", []):
                add("country", lit(code))
            for lang, label in f["label"].items():
                add("label", lit(label, lang))
            for title, lang in f.get("title", []):
                add("title", lit(title, lang))
            for alias in f.get("alias", []):
                add("alias", lit(alias, "en"))
            add("sl", lit(f["sl"]))
            for key in ("desc", "enwiki", "imdb", "tmdb"):
                if key in f:
                    add(key, lit(f[key], "en" if key == "desc" else None))
            if "poster" in f:
                add("poster", {"type": "uri", "value": f["poster"]})
        return rows

    def dates(self, query: str) -> list[dict[str, Any]]:
        rows = []
        for q in _values(query):
            f = FILMS.get(q, {})
            for t, precision, country in f.get("dates", []):
                row = {
                    "f": uri(q),
                    "k": lit("date"),
                    "t": lit(t),
                    "p": lit(precision),
                    "rank": {"type": "uri", "value": RANK},
                }
                if country:
                    row["x"] = lit(country)
                rows.append(row)
            for amount, unit, rank in f.get("runtime", []):
                rows.append(
                    {
                        "f": uri(q),
                        "k": lit("runtime"),
                        "t": lit(amount),
                        "rank": {"type": "uri", "value": rank},
                        "x": uri(unit),
                    }
                )
        return rows

    def credits(self, query: str) -> list[dict[str, Any]]:
        rows = []
        for q in _values(query):
            for role, person, order, character in FILMS.get(q, {}).get("credits", []):
                row = {"f": uri(q), "k": lit(role), "p": uri(person)}
                if order:
                    row["o"] = lit(order)
                if character:
                    row["c"] = lit(character)
                rows.append(row)
        return rows

    def people(self, query: str) -> list[dict[str, Any]]:
        rows = []
        for p in _values(query):
            if p in PEOPLE:
                name, links = PEOPLE[p]
                rows.append({"p": uri(p), "l": lit(name, "en"), "sl": lit(links)})
        return rows

    def commons(self, request: httpx.Request) -> httpx.Response:
        self.calls.append("commons")
        return httpx.Response(
            200,
            json={
                "query": {
                    "normalized": [],
                    "pages": [
                        {
                            "title": "File:Stalker poster.jpg",
                            "imageinfo": [
                                {
                                    "thumburl": "https://upload.wikimedia.org/stalker-400.jpg",
                                    "thumbwidth": 400,
                                    "thumbheight": 580,
                                    "descriptionurl": "https://commons.wikimedia.org/wiki/File:Stalker_poster.jpg",
                                    "extmetadata": {
                                        "LicenseShortName": {"value": "Public domain"},
                                        "Artist": {"value": "<a href='x'>Mosfilm</a>"},
                                    },
                                }
                            ],
                        }
                    ],
                }
            },
        )


def make_provider(fake: FakeWikidata, batch_size: int = 3) -> tuple[wikidata.WikidataProvider, list[float]]:
    sleeps: list[float] = []
    client = wikidata.WikidataClient(
        httpx.Client(transport=httpx.MockTransport(fake)),
        "https://query.wikidata.org/sparql",
        "https://commons.wikimedia.org/w/api.php",
        max_retries=2,
        sleep=sleeps.append,
    )
    provider = wikidata.WikidataProvider(
        client, batch_size=batch_size, root_types=("Q11424", "Q24862"), today=date(2026, 10, 26)
    )
    return provider, sleeps


GENRES = [(slug, wikidata.GENRE_NAMES[slug]) for slug in wikidata.GENRES]


@pytest.fixture
def clean(engine: Engine) -> Iterator[Engine]:
    """Removes everything a Wikidata test wrote, leaving the fixture catalog as the other tests expect it."""
    yield engine
    keep = [slug for slug, _ in fixtures.FixtureProvider().genres()]
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM movie WHERE id IN (SELECT movie_id FROM external_id WHERE provider = 'wikidata')")
        )
        conn.execute(text("DELETE FROM person WHERE provider = 'wikidata'"))
        conn.execute(text("DELETE FROM genre WHERE slug <> ALL(:keep)"), {"keep": keep})
        conn.execute(text("DELETE FROM import_run"))
    with Session(engine) as session, session.begin():
        importer.finish_catalog(session, fixtures.VERSION, [fixtures.PROVIDER])


def wd_id(engine: Engine, qid: str) -> str:
    with engine.connect() as conn:
        return str(
            conn.execute(
                text("SELECT movie_id FROM external_id WHERE provider = 'wikidata' AND external_id = :q"), {"q": qid}
            ).scalar_one()
        )


def wikidata_counts(engine: Engine) -> dict[str, int]:
    with engine.connect() as conn:
        return {
            "movies": conn.execute(text("SELECT count(*) FROM external_id WHERE provider = 'wikidata'")).scalar_one(),
            "titles": conn.execute(text("SELECT count(*) FROM alternate_title WHERE source = 'wikidata'")).scalar_one(),
            "credits": conn.execute(
                text("SELECT count(*) FROM credit c JOIN person p ON p.id = c.person_id WHERE p.provider = 'wikidata'")
            ).scalar_one(),
            "people": conn.execute(text("SELECT count(*) FROM person WHERE provider = 'wikidata'")).scalar_one(),
        }


def test_maps_wikidata_to_catalog(clean: Engine, client: TestClient) -> None:
    fake = FakeWikidata()
    provider, _ = make_provider(fake)
    assert cli.run_import(clean, provider, resume=False, genres=GENRES) == 0

    # Adult films are not imported; everything else is, once.
    assert wikidata_counts(clean)["movies"] == 6

    stalker_id = wd_id(clean, "Q101")
    found = client.get("/api/v1/movies", params={"q": "Сталкер", "limit": 48}).json()["items"]
    assert stalker_id in [m["id"] for m in found]
    detail = client.get(f"/api/v1/movies/{stalker_id}").json()
    assert detail["original_title"] == "Сталкер"
    assert detail["original_language"] == "ru"
    assert detail["release"] == {"status": "released", "date": "1979-05-25", "country": "SU"}
    # Preferred rank wins: 2.7 hours.
    assert detail["runtime_minutes"] == 162
    assert detail["description"] == "1979 film by Andrei Tarkovsky"
    assert [g["slug"] for g in detail["genres"]] == ["drama"]
    assert detail["directors"] == [{"id": detail["directors"][0]["id"], "name": "Andrei Tarkovsky"}]
    assert detail["poster"]["url"] == "https://upload.wikimedia.org/stalker-400.jpg"
    assert detail["poster"]["source"] == {
        "name": "Wikimedia Commons",
        "kind": "provider",
        "attribution": "Mosfilm",
        "license": "Public domain",
        "url": "https://commons.wikimedia.org/wiki/File:Stalker_poster.jpg",
    }
    sources = {s["name"]: s for s in detail["provenance"]["sources"]}
    assert sources["Wikidata"]["url"] == "https://www.wikidata.org/wiki/Q101"
    assert sources["IMDb"]["url"] == "https://www.imdb.com/title/tt0079944/"
    assert sources["TMDB"]["external_id"] == "1398"
    assert sources["Wikipedia"]["url"] == "https://en.wikipedia.org/wiki/Stalker_%281979_film%29"
    assert detail["provenance"]["catalog_version"].startswith("wikidata-")

    credits = client.get(f"/api/v1/movies/{stalker_id}/credits").json()
    # The stated series ordinal comes first, then better-known people.
    assert [c["person"]["name"] for c in credits["cast"]] == ["Anatoly Solonitsyn", "Alexander Kaidanovsky"]
    assert credits["cast"][1]["character"] == "Stalker"

    jetee = client.get(f"/api/v1/movies/{wd_id(clean, 'Q102')}").json()
    assert (jetee["title"], jetee["year"], jetee["kind"], jetee["runtime_minutes"]) == ("La Jetée", 1962, "short", 28)
    assert jetee["release"]["date"] is None  # year precision never becomes January 1
    assert jetee["directors"][0]["name"] == "Chris Marker"
    assert client.get("/api/v1/movies", params={"q": "la jetee"}).json()["items"][0]["id"] == jetee["id"]

    assert client.get(f"/api/v1/movies/{wd_id(clean, 'Q103')}").json()["kind"] == "tv"
    future = client.get(f"/api/v1/movies/{wd_id(clean, 'Q105')}").json()
    assert future["release"] == {"status": "announced", "date": "2031-03-01", "country": None}
    assert client.get(f"/api/v1/movies/{wd_id(clean, 'Q106')}").json()["release"]["status"] == "unknown"
    assert client.get("/api/v1/movies", params={"q": "adult film"}).json()["items"] == []

    shown = client.get("/api/v1/movies", params={"exclude": ["short", "tv", "unreleased"], "limit": 48}).json()
    ids = {m["id"] for m in shown["items"]}
    assert stalker_id in ids
    assert not ids & {jetee["id"], future["id"], wd_id(clean, "Q103")}
    # Best known first when browsing.
    assert client.get("/api/v1/movies", params={"limit": 1}).json()["items"][0]["title"] == "Stalker"


def test_reimport_updates_in_place(clean: Engine, client: TestClient) -> None:
    provider, _ = make_provider(FakeWikidata())
    assert cli.run_import(clean, provider, resume=False, genres=GENRES) == 0
    before = wikidata_counts(clean)
    first_id = wd_id(clean, "Q102")

    provider, _ = make_provider(FakeWikidata())
    assert cli.run_import(clean, provider, resume=False, genres=GENRES) == 0
    assert wikidata_counts(clean) == before
    assert wd_id(clean, "Q102") == first_id
    with clean.connect() as conn:
        runs = conn.execute(text("SELECT imported, updated, failed, status FROM import_run ORDER BY id")).all()
    assert [tuple(r) for r in runs] == [(6, 0, 0, "completed"), (0, 6, 0, "completed")]


def test_failure_then_resume(clean: Engine) -> None:
    fake = FakeWikidata()
    # Batches are Q101-103, Q104-106, Q107. The second batch's credits query is refused.
    fake.fail_on = ("credits", 2)
    provider, _ = make_provider(fake, batch_size=3)
    assert cli.run_import(clean, provider, resume=False, genres=GENRES) == 1
    with clean.connect() as conn:
        run = conn.execute(text("SELECT id, status, imported, checkpoint, error FROM import_run")).one()
    assert run.status == "failed"
    assert run.imported == 3
    assert run.checkpoint["after_qid"] == 103
    assert "HTTP 400" in run.error
    assert wikidata_counts(clean)["movies"] == 3

    provider, _ = make_provider(FakeWikidata(), batch_size=3)
    assert cli.run_import(clean, provider, resume=True, genres=GENRES) == 0
    with clean.connect() as conn:
        runs = conn.execute(text("SELECT id, status, imported, updated FROM import_run")).all()
    assert [(r.id, r.status, r.imported, r.updated) for r in runs] == [(run.id, "completed", 6, 0)]
    assert wikidata_counts(clean)["movies"] == 6


def test_rate_limit_honours_retry_after() -> None:
    fake = FakeWikidata()
    fake.fail = {"listing": 1}
    fake.fail_status = 429
    fake.fail_headers = {"Retry-After": "7"}
    provider, sleeps = make_provider(fake)
    assert provider.list_qids() == [101, 102, 103, 104, 105, 106, 107]
    assert sleeps == [7.0]


def test_server_errors_back_off_then_give_up() -> None:
    fake = FakeWikidata()
    fake.fail = {"listing": 99}
    fake.fail_status = 503
    provider, sleeps = make_provider(fake)
    with pytest.raises(wikidata.WikidataError, match="503"):
        provider.list_qids()
    assert sleeps == [2.0, 4.0]


def test_failed_batch_is_split_before_giving_up() -> None:
    fake = FakeWikidata()
    provider, _ = make_provider(fake)
    seen_sizes: list[int] = []
    original = provider._fetch

    def fetch(qids: list[str], maps: wikidata.Maps) -> list[Any]:
        seen_sizes.append(len(qids))
        if len(qids) > 60:
            raise wikidata.WikidataError("timeout")
        return original(qids, maps)

    provider._fetch = fetch  # type: ignore[method-assign]
    maps = provider.resolve_maps()
    qids = [f"Q{n}" for n in range(1000, 1100)] + ["Q101"]
    records = provider.fetch(qids, maps)
    assert seen_sizes[0] == 101
    assert [r.external_id for r in records] == ["Q101"]


def test_invalid_records_are_counted_not_fatal(clean: Engine) -> None:
    with Session(clean) as session, session.begin():
        report = importer.upsert_movies(
            session,
            [
                MovieIn(provider="wikidata", external_id="Q900", canonical_title="Fine"),
                MovieIn(provider="wikidata", external_id="Q901", canonical_title="?!"),
                MovieIn(provider="wikidata", external_id="Q902", canonical_title="Bad year", release_year=12),
            ],
        )
    assert (report.imported, report.updated, report.failed) == (1, 0, 2)
    assert len(report.errors) == 2


def test_fixture_seed_is_idempotent(engine: Engine) -> None:
    with engine.connect() as conn:
        before = conn.execute(text("SELECT count(*) FROM alternate_title")).scalar_one()
    report = cli.seed_fixtures(engine)
    assert (report.imported, report.updated, report.failed) == (0, 43, 0)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM movie")).scalar_one() == 43
        assert conn.execute(text("SELECT count(*) FROM alternate_title")).scalar_one() == before
