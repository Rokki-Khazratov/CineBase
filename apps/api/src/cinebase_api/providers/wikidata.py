"""Film catalog from Wikidata (CC0). Posters only when Wikimedia Commons has a freely licensed file.

The import lists every item that is an instance of a film type, then fetches details for batches of items
in a few SPARQL queries (facts and names, dates and runtimes, credits, then people). Batches are ordered by
numeric QID, so a checkpoint is just the last QID written and a resumed run continues after it.
"""

import logging
import re
import time
from collections import defaultdict
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

import httpx

from ..models import NAME_ALTERNATE
from .base import AssetIn, CreditIn, MovieIn, PersonIn, TitleIn

log = logging.getLogger("cinebase.import.wikidata")

PROVIDER = "wikidata"
ENTITY = "http://www.wikidata.org/entity/"

# Items that are an instance of one of these are listed. Together they cover features, shorts, TV films,
# animated, documentary and silent films; an item listed under several types is imported once.
ROOT_TYPES = ("Q11424", "Q24862", "Q506240", "Q202866", "Q93204", "Q29168811", "Q226730", "Q17517379")

# Our genre slug -> Wikidata classes whose subclasses (P279*) count as that genre.
GENRES: dict[str, tuple[str, ...]] = {
    "action": ("Q188473",),
    "adventure": ("Q319221",),
    "animation": ("Q202866",),
    "comedy": ("Q157443",),
    "crime": ("Q959790",),
    "documentary": ("Q93204",),
    "drama": ("Q130232",),
    "family": ("Q1361932", "Q2143665"),
    "fantasy": ("Q157394",),
    "history": ("Q17013749",),
    "horror": ("Q200092",),
    "music": ("Q842256",),
    "mystery": ("Q1200678",),
    "romance": ("Q1054574",),
    "science-fiction": ("Q471839",),
    "thriller": ("Q2484376",),
    "war": ("Q369747",),
    "western": ("Q172980",),
}
GENRE_NAMES = {
    "action": "Action",
    "adventure": "Adventure",
    "animation": "Animation",
    "comedy": "Comedy",
    "crime": "Crime",
    "documentary": "Documentary",
    "drama": "Drama",
    "family": "Family",
    "fantasy": "Fantasy",
    "history": "History",
    "horror": "Horror",
    "music": "Music",
    "mystery": "Mystery",
    "romance": "Romance",
    "science-fiction": "Science fiction",
    "thriller": "Thriller",
    "war": "War",
    "western": "Western",
}
SHORT_ROOT, TV_ROOT, ADULT_ROOT = "Q24862", "Q506240", "Q185529"
# Academy rule of thumb: 40 minutes or less is a short.
SHORT_MAX_MINUTES = 40
MAX_CAST = 30

UNIT_MINUTES = {"Q7727": 1.0, "Q25235": 60.0, "Q11574": 1 / 60, "Q199": 1.0}
CREDIT_JOBS = {
    "director": ("Directing", "Director"),
    "writer": ("Writing", "Writer"),
    "dop": ("Camera", "Director of Photography"),
    "composer": ("Sound", "Original Music Composer"),
    "cast": ("Acting", "Actor"),
}
PERSON_LANGS = ("en", "mul", "de", "fr", "es", "it", "pt", "nl", "sv", "pl", "ru", "ja", "zh", "ko")
_TAGS = re.compile(r"<[^>]+>")
_IMDB_TITLE = re.compile(r"^tt\d{7,9}$")


class WikidataError(Exception):
    """A request failed after all retries. The import stops and can be resumed."""


@dataclass
class Maps:
    """Class sets resolved once per run (and kept in the checkpoint, so a resumed run uses the same ones)."""

    genres: dict[str, set[str]]
    short: set[str]
    tv: set[str]
    adult: set[str]

    def to_json(self) -> dict[str, Any]:
        return {
            "genres": {k: sorted(v) for k, v in self.genres.items()},
            "short": sorted(self.short),
            "tv": sorted(self.tv),
            "adult": sorted(self.adult),
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "Maps":
        return cls(
            genres={k: set(v) for k, v in data["genres"].items()},
            short=set(data["short"]),
            tv=set(data["tv"]),
            adult=set(data["adult"]),
        )


def qid_of(value: str) -> str:
    return value.removeprefix(ENTITY)


def qnum(qid: str) -> int:
    return int(qid.lstrip("Q"))


def strip_html(value: str) -> str:
    return re.sub(r"\s+", " ", _TAGS.sub("", value)).strip()


class WikidataClient:
    """Polite HTTP access: one request at a time, retries with backoff, honours 429 Retry-After."""

    def __init__(
        self,
        client: httpx.Client,
        sparql_url: str,
        commons_url: str,
        max_retries: int = 5,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.client = client
        self.sparql_url = sparql_url
        self.commons_url = commons_url
        self.max_retries = max_retries
        self.sleep = sleep
        self.requests = 0

    def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        delay = 2.0
        last = ""
        for attempt in range(self.max_retries + 1):
            self.requests += 1
            try:
                response = self.client.request(method, url, **kwargs)
            except httpx.TransportError as exc:
                last = f"{type(exc).__name__}"
            else:
                if response.status_code == 200:
                    return response
                last = f"HTTP {response.status_code}"
                if response.status_code == 429:
                    retry_after = response.headers.get("retry-after", "")
                    wait = float(retry_after) if retry_after.isdigit() else delay
                    log.warning("rate limited, waiting %.0fs", wait)
                    self.sleep(min(wait, 300.0))
                    continue
                if response.status_code not in (500, 502, 503, 504):
                    raise WikidataError(f"{last} from {url}: {response.text[:200]}")
            if attempt < self.max_retries:
                log.warning("%s, retrying in %.0fs", last, delay)
                self.sleep(delay)
                delay = min(delay * 2, 120.0)
        raise WikidataError(f"{last} from {url} after {self.max_retries + 1} attempts")

    def sparql(self, query: str) -> list[dict[str, dict[str, str]]]:
        response = self._request(
            "POST",
            self.sparql_url,
            data={"query": query},
            headers={"Accept": "application/sparql-results+json"},
        )
        try:
            bindings: list[dict[str, dict[str, str]]] = response.json()["results"]["bindings"]
        except (ValueError, KeyError) as exc:
            raise WikidataError(f"unreadable SPARQL response: {exc}") from None
        return bindings

    def commons_files(self, files: list[str]) -> dict[str, dict[str, Any]]:
        """File name -> imageinfo (thumbnail URL and size, license, author). Missing files are left out."""
        out: dict[str, dict[str, Any]] = {}
        for i in range(0, len(files), 50):
            chunk = files[i : i + 50]
            response = self._request(
                "GET",
                self.commons_url,
                params={
                    "action": "query",
                    "format": "json",
                    "formatversion": "2",
                    "prop": "imageinfo",
                    "iiprop": "url|size|extmetadata",
                    "iiurlwidth": "400",
                    "iiextmetadatafilter": "LicenseShortName|Artist|UsageTerms",
                    "titles": "|".join("File:" + f for f in chunk),
                },
            )
            data = response.json().get("query", {})
            renamed = {n["to"]: n["from"] for n in data.get("normalized", [])}
            for page in data.get("pages", []):
                info = (page.get("imageinfo") or [None])[0]
                if not info:
                    continue
                title = renamed.get(page["title"], page["title"])
                out[title.removeprefix("File:")] = info
        return out


class WikidataProvider:
    name = PROVIDER

    def __init__(
        self,
        client: WikidataClient,
        batch_size: int = 1000,
        limit: int | None = None,
        root_types: tuple[str, ...] = ROOT_TYPES,
        today: date | None = None,
    ) -> None:
        self.client = client
        self.batch_size = batch_size
        self.limit = limit
        self.root_types = root_types
        self.today = today or datetime.now(UTC).date()
        self.people: dict[str, tuple[str, int] | None] = {}

    # --- setup --------------------------------------------------------------------------------------

    def _subclasses(self, roots: tuple[str, ...]) -> set[str]:
        values = " ".join("wd:" + r for r in roots)
        rows = self.client.sparql(f"SELECT DISTINCT ?c WHERE {{ VALUES ?r {{ {values} }} ?c wdt:P279* ?r }}")
        return {qid_of(r["c"]["value"]) for r in rows} | set(roots)

    def resolve_maps(self) -> Maps:
        genres = {slug: self._subclasses(roots) for slug, roots in GENRES.items()}
        return Maps(
            genres=genres,
            short=self._subclasses((SHORT_ROOT, "Q17517379")),
            tv=self._subclasses((TV_ROOT,)),
            adult=self._subclasses((ADULT_ROOT,)),
        )

    def list_qids(self) -> list[int]:
        found: set[int] = set()
        for root in self.root_types:
            rows = self.client.sparql(f"SELECT ?f WHERE {{ ?f wdt:P31 wd:{root} }}")
            found.update(qnum(qid_of(r["f"]["value"])) for r in rows if r["f"]["value"].startswith(ENTITY + "Q"))
            log.info("listed %s: %d items so far", root, len(found))
        return sorted(found)

    # --- batches ------------------------------------------------------------------------------------

    def batches(self, checkpoint: dict[str, Any]) -> Iterator[tuple[list[MovieIn], dict[str, Any]]]:
        maps = Maps.from_json(checkpoint["maps"]) if "maps" in checkpoint else self.resolve_maps()
        after = int(checkpoint.get("after_qid", 0))
        qids = [q for q in self.list_qids() if q > after]
        if self.limit is not None:
            qids = qids[: max(0, self.limit - int(checkpoint.get("seen", 0)))]
        seen = int(checkpoint.get("seen", 0))
        total = seen + len(qids)
        for i in range(0, len(qids), self.batch_size):
            chunk = [f"Q{q}" for q in qids[i : i + self.batch_size]]
            records = self.fetch(chunk, maps)
            seen += len(chunk)
            log.info("batch up to %s: %d records (%d/%d items)", chunk[-1], len(records), seen, total)
            yield records, {"maps": maps.to_json(), "after_qid": qnum(chunk[-1]), "seen": seen, "total": total}

    def fetch(self, qids: list[str], maps: Maps) -> list[MovieIn]:
        """Details for one batch. A batch that keeps timing out is split in half rather than given up on."""
        try:
            return self._fetch(qids, maps)
        except WikidataError:
            if len(qids) <= 50:
                raise
            mid = len(qids) // 2
            log.warning("batch of %d failed, splitting", len(qids))
            return self.fetch(qids[:mid], maps) + self.fetch(qids[mid:], maps)

    def _fetch(self, qids: list[str], maps: Maps) -> list[MovieIn]:
        values = _values(qids)
        timings: dict[str, float] = {}

        def timed(name: str, query: str) -> list[dict[str, dict[str, str]]]:
            started = time.monotonic()
            rows = self.client.sparql(query.replace("%VALUES%", values))
            timings[name] = time.monotonic() - started
            return rows

        facts = timed("facts", FACTS_QUERY)
        dates = timed("dates", DATES_QUERY)
        credits = timed("credits", CREDITS_QUERY)

        by_film: dict[str, dict[str, list[dict[str, str]]]] = defaultdict(lambda: defaultdict(list))
        for row in facts:
            by_film[qid_of(row["f"]["value"])][row["k"]["value"]].append(row["v"])
        date_rows: dict[str, list[dict[str, dict[str, str]]]] = defaultdict(list)
        for row in dates:
            date_rows[qid_of(row["f"]["value"])].append(row)
        credit_rows: dict[str, list[dict[str, dict[str, str]]]] = defaultdict(list)
        for row in credits:
            if row["p"]["type"] == "uri" and row["p"]["value"].startswith(ENTITY):
                credit_rows[qid_of(row["f"]["value"])].append(row)

        started = time.monotonic()
        self._load_people({qid_of(r["p"]["value"]) for rows in credit_rows.values() for r in rows})
        timings["people"] = time.monotonic() - started
        poster_files = sorted({v["value"].rsplit("/", 1)[-1] for f in by_film.values() for v in f.get("poster", [])})
        posters = self.client.commons_files([_commons_name(f) for f in poster_files]) if poster_files else {}

        records = []
        for qid in qids:
            record = self.build(
                qid, by_film.get(qid, {}), date_rows.get(qid, []), credit_rows.get(qid, []), posters, maps
            )
            if record is not None:
                records.append(record)
        log.info("fetched %d items: %s", len(qids), ", ".join(f"{k} {v:.1f}s" for k, v in timings.items()))
        return records

    def _load_people(self, qids: set[str]) -> None:
        """Name and notability per person, cached for the run. English/multilingual labels first, since
        asking for many languages at once is the slowest query of a batch; other languages only as fallback."""
        missing = sorted(q for q in qids if q not in self.people)
        for i in range(0, len(missing), 2500):
            chunk = missing[i : i + 2500]
            names: dict[str, dict[str, str]] = defaultdict(dict)
            links: dict[str, int] = {}
            rows = self.client.sparql(
                f"SELECT ?p ?l ?sl WHERE {{ VALUES ?p {{ {_values(chunk)} }} OPTIONAL {{ ?p wikibase:sitelinks ?sl }} "
                'OPTIONAL { ?p rdfs:label ?l FILTER(LANG(?l) = "en" || LANG(?l) = "mul") } }'
            )
            unnamed = self._collect(rows, names, links)
            if unnamed - set(names):
                rest = sorted(unnamed - set(names))
                langs = ", ".join(f'"{lang}"' for lang in PERSON_LANGS[2:])
                rows = self.client.sparql(
                    f"SELECT ?p ?l WHERE {{ VALUES ?p {{ {_values(rest)} }} "
                    f"?p rdfs:label ?l FILTER(LANG(?l) IN ({langs})) }}"
                )
                self._collect(rows, names, links)
            for pid in chunk:
                label = next((names[pid][lang] for lang in PERSON_LANGS if lang in names[pid]), None)
                self.people[pid] = (label, links.get(pid, 0)) if label else None

    @staticmethod
    def _collect(
        rows: list[dict[str, dict[str, str]]], names: dict[str, dict[str, str]], links: dict[str, int]
    ) -> set[str]:
        seen = set()
        for row in rows:
            pid = qid_of(row["p"]["value"])
            seen.add(pid)
            if "sl" in row:
                links[pid] = int(row["sl"]["value"])
            if "l" in row:
                names[pid][row["l"].get("xml:lang", "")] = row["l"]["value"]
        return seen

    # --- one film -----------------------------------------------------------------------------------

    def build(
        self,
        qid: str,
        facts: dict[str, list[dict[str, str]]],
        dates: list[dict[str, dict[str, str]]],
        credits: list[dict[str, dict[str, str]]],
        posters: dict[str, dict[str, Any]],
        maps: Maps,
    ) -> MovieIn | None:
        types = {qid_of(v["value"]) for v in facts.get("type", [])}
        genre_items = {qid_of(v["value"]) for v in facts.get("genre", [])}
        if (types | genre_items) & maps.adult:
            return None

        labels: dict[str, str] = {}
        for v in facts.get("label", []):
            labels.setdefault(v.get("xml:lang", ""), v["value"])
        official = sorted(facts.get("title", []), key=lambda v: (v.get("xml:lang", ""), v["value"]))
        languages = sorted({v["value"] for v in facts.get("lang", [])})
        original_language = languages[0] if len(languages) == 1 else None
        if official and not original_language:
            original_language = official[0].get("xml:lang") or None
        title = (
            labels.get("en")
            or labels.get("mul")
            or (official[0]["value"] if official else None)
            or (labels.get(original_language) if original_language else None)
            or next(iter(sorted(labels.items())), ("", None))[1]
        )
        if not title:
            return None
        original = next((v["value"] for v in official if v["value"] != title), None)
        if original is None and original_language and labels.get(original_language, title) != title:
            original = labels[original_language]

        release_date, release_year, country = _release(dates)
        runtime = _runtime(dates)
        if release_date and release_date > self.today or (release_year and release_year > self.today.year):
            status = "announced"
        elif release_year is not None:
            status = "released"
        else:
            status = "unknown"

        if types & maps.tv:
            kind = "tv"
        elif types & maps.short or (runtime is not None and runtime <= SHORT_MAX_MINUTES):
            kind = "short"
        else:
            kind = "feature"

        genres = [slug for slug, classes in maps.genres.items() if (genre_items | types) & classes]

        titles = [TitleIn(text, lang or None, NAME_ALTERNATE) for lang, text in sorted(labels.items())]
        titles += [TitleIn(v["value"], v.get("xml:lang") or None, NAME_ALTERNATE) for v in official]
        titles += [TitleIn(v["value"], "en", NAME_ALTERNATE) for v in facts.get("alias", [])]

        links: list[tuple[str, str]] = []
        imdb = sorted(v["value"] for v in facts.get("imdb", []) if _IMDB_TITLE.match(v["value"]))
        if imdb:
            links.append(("imdb", imdb[0]))
        tmdb = sorted((v["value"] for v in facts.get("tmdb", []) if v["value"].isdigit()), key=int)
        if tmdb:
            links.append(("tmdb", tmdb[0]))
        if facts.get("enwiki"):
            links.append(("enwiki", facts["enwiki"][0]["value"]))

        assets = []
        for v in facts.get("poster", []):
            name = _commons_name(v["value"].rsplit("/", 1)[-1])
            info = posters.get(name)
            license_name = ((info or {}).get("extmetadata", {}).get("LicenseShortName") or {}).get("value")
            if not info or not license_name or not info.get("thumburl"):
                continue
            artist = strip_html(((info.get("extmetadata") or {}).get("Artist") or {}).get("value", "")) or None
            assets.append(
                AssetIn(
                    kind="poster",
                    url=info["thumburl"],
                    width=info.get("thumbwidth"),
                    height=info.get("thumbheight"),
                    source="Wikimedia Commons",
                    source_kind="provider",
                    attribution=artist,
                    license=strip_html(license_name),
                    source_url=info.get("descriptionurl"),
                )
            )
            break

        sitelinks = max((int(v["value"]) for v in facts.get("sl", [])), default=0)
        description = facts["desc"][0]["value"] if facts.get("desc") else None
        countries = sorted({v["value"] for v in facts.get("country", [])})
        return MovieIn(
            provider=PROVIDER,
            external_id=qid,
            canonical_title=title,
            original_title=original,
            original_language=(original_language or "")[:16] or None,
            release_date=release_date,
            release_year=release_year,
            release_country=country or (countries[0] if len(countries) == 1 else None),
            runtime_minutes=runtime,
            description=description,
            status=status,
            kind=kind,
            notability=sitelinks,
            genres=genres,
            titles=titles,
            credits=self._credits(credits),
            assets=assets,
            links=links,
            payload={
                "types": sorted(types),
                "genres": sorted(genre_items),
                "languages": languages,
                "countries": countries,
                "sitelinks": sitelinks,
            },
        )

    def _credits(self, rows: list[dict[str, dict[str, str]]]) -> list[CreditIn]:
        grouped: dict[str, dict[str, tuple[int | None, str | None]]] = defaultdict(dict)
        for row in rows:
            role = row["k"]["value"]
            pid = qid_of(row["p"]["value"])
            if role not in CREDIT_JOBS or self.people.get(pid) is None:
                continue
            order_text = row.get("o", {}).get("value", "")
            order = int(order_text) if order_text.isdigit() else None
            character = row.get("c", {}).get("value") or None
            previous = grouped[role].get(pid)
            if previous is None or (order is not None and (previous[0] is None or order < previous[0])):
                grouped[role][pid] = (order, character or (previous[1] if previous else None))
        out: list[CreditIn] = []
        position = 0
        for role in ("director", "cast", "writer", "dop", "composer"):
            people = grouped.get(role, {})

            # Wikidata has no billing order. Use the series ordinal when given, else the better-known first.
            def rank(pid: str, people: dict[str, tuple[int | None, str | None]] = people) -> tuple[int, int, int, int]:
                order, _ = people[pid]
                person = self.people[pid]
                return (0 if order is not None else 1, order or 0, -(person[1] if person else 0), qnum(pid))

            chosen = sorted(people, key=rank)
            if role == "cast":
                chosen = chosen[:MAX_CAST]
            department, job = CREDIT_JOBS[role]
            for pid in chosen:
                person = self.people[pid]
                assert person is not None
                out.append(
                    CreditIn(
                        person=PersonIn(provider=PROVIDER, external_id=pid, name=person[0], notability=person[1]),
                        department=department,
                        job=job,
                        character=people[pid][1],
                        order=position,
                    )
                )
                position += 1
        return out


def _values(qids: list[str]) -> str:
    return " ".join("wd:" + q for q in qids)


def _commons_name(file_url_part: str) -> str:
    """Commons file name from a Special:FilePath URL segment, with spaces as in page titles."""
    return httpx.URL("https://x/" + file_url_part).path.removeprefix("/").replace("_", " ")


def _release(rows: list[dict[str, dict[str, str]]]) -> tuple[date | None, int | None, str | None]:
    """Earliest publication date. A day is kept only when Wikidata states it to the day (precision 11)."""
    best: tuple[int, date | None, str | None] | None = None
    for row in rows:
        if row["k"]["value"] != "date" or row["rank"]["value"].endswith("DeprecatedRank") or "p" not in row:
            continue
        precision = int(row["p"]["value"])
        match = re.match(r"^(\+|-)?(\d{1,})-(\d{2})-(\d{2})", row["t"]["value"])
        if precision < 9 or not match or match.group(1) == "-":
            continue
        year = int(match.group(2))
        day = None
        if precision >= 11:
            try:
                day = date(year, int(match.group(3)), int(match.group(4)))
            except ValueError:
                day = None
        country = row.get("x", {}).get("value")
        candidate = (year, day, country)
        if best is None or (year, day or date.max) < (best[0], best[1] or date.max):
            best = candidate
    if best is None:
        return None, None, None
    return best[1], best[0], best[2]


def _runtime(rows: list[dict[str, dict[str, str]]]) -> int | None:
    """Preferred-rank duration if there is one, else the shortest stated (usually the release cut)."""
    values: list[tuple[int, float]] = []
    for row in rows:
        if row["k"]["value"] != "runtime" or row["rank"]["value"].endswith("DeprecatedRank"):
            continue
        unit = qid_of(row.get("x", {}).get("value", ""))
        factor = UNIT_MINUTES.get(unit)
        try:
            amount = float(row["t"]["value"])
        except ValueError:
            continue
        if factor is None or amount <= 0:
            continue
        preferred = 0 if row["rank"]["value"].endswith("PreferredRank") else 1
        values.append((preferred, amount * factor))
    if not values:
        return None
    minutes = round(min(values)[1])
    return minutes if 0 < minutes < 32767 else None


FACTS_QUERY = """SELECT ?f ?k ?v WHERE { VALUES ?f { %VALUES% }
{ ?f wdt:P31 ?v BIND("type" AS ?k) } UNION { ?f wdt:P136 ?v BIND("genre" AS ?k) }
UNION { ?f wdt:P364/wdt:P218 ?v BIND("lang" AS ?k) } UNION { ?f wdt:P495/wdt:P297 ?v BIND("country" AS ?k) }
UNION { ?f wdt:P3383 ?v BIND("poster" AS ?k) } UNION { ?f wdt:P345 ?v BIND("imdb" AS ?k) }
UNION { ?f wdt:P4947 ?v BIND("tmdb" AS ?k) } UNION { ?f wikibase:sitelinks ?v BIND("sl" AS ?k) }
UNION { ?f schema:description ?v FILTER(LANG(?v) = "en") BIND("desc" AS ?k) }
UNION { ?a schema:about ?f ; schema:isPartOf <https://en.wikipedia.org/> ; schema:name ?v BIND("enwiki" AS ?k) }
UNION { ?f wdt:P1476 ?v BIND("title" AS ?k) } UNION { ?f rdfs:label ?v BIND("label" AS ?k) }
UNION { ?f skos:altLabel ?v FILTER(LANG(?v) = "en") BIND("alias" AS ?k) }
}"""

DATES_QUERY = """SELECT ?f ?k ?t ?p ?rank ?x WHERE { VALUES ?f { %VALUES% }
{ ?f p:P577 ?st . ?st psv:P577 [ wikibase:timeValue ?t ; wikibase:timePrecision ?p ] ; wikibase:rank ?rank .
  OPTIONAL { ?st pq:P291/wdt:P297 ?x } BIND("date" AS ?k) }
UNION { ?f p:P2047 ?st . ?st psv:P2047 [ wikibase:quantityAmount ?t ; wikibase:quantityUnit ?x ] ;
  wikibase:rank ?rank . BIND("runtime" AS ?k) }
}"""

CREDITS_QUERY = """SELECT ?f ?k ?p ?o ?c WHERE { VALUES ?f { %VALUES% }
VALUES (?k ?pp ?ps) { ("director" p:P57 ps:P57) ("cast" p:P161 ps:P161) ("writer" p:P58 ps:P58)
  ("dop" p:P344 ps:P344) ("composer" p:P86 ps:P86) }
?f ?pp ?st . ?st ?ps ?p .
OPTIONAL { ?st pq:P1545 ?o } OPTIONAL { ?st pq:P4633 ?c }
}"""
