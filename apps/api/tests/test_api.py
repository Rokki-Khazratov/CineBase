from typing import Any

import pytest
from fastapi.testclient import TestClient


def movies(client: TestClient, **params: Any) -> dict[str, Any]:
    response = client.get("/api/v1/movies", params=params)
    assert response.status_code == 200, response.text
    data: dict[str, Any] = response.json()
    return data


def labels(page: dict[str, Any]) -> list[str]:
    return [f"{m['title']} ({m['year']})" for m in page["items"]]


def first(client: TestClient, q: str) -> str:
    return labels(movies(client, q=q))[0]


def test_health(client: TestClient) -> None:
    assert client.get("/health/live").json() == {"status": "ok"}
    assert client.get("/health/ready").json() == {"status": "ok"}


def test_same_title_told_apart_by_year(client: TestClient) -> None:
    page = movies(client, q="suspiria")
    assert sorted(labels(page)[:2]) == ["Suspiria (1977)", "Suspiria (2018)"]
    assert sorted(m["directors"][0]["name"] for m in page["items"][:2]) == ["Dario Argento", "Luca Guadagnino"]


def test_title_year_puts_that_year_first(client: TestClient) -> None:
    assert labels(movies(client, q="Suspiria (2018)"))[:2] == ["Suspiria (2018)", "Suspiria (1977)"]
    assert first(client, "The Thing (2011)") == "The Thing (2011)"


def test_case_accents_punctuation(client: TestClient) -> None:
    assert first(client, "AMELIE") == "Amélie (2001)"
    assert first(client, "oceans 11") == "Ocean's 11 (1960)"
    assert first(client, "paris texas") == "Paris, Texas (1984)"


def test_original_and_alternate_titles(client: TestClient) -> None:
    assert first(client, "Солярис") == "Solaris (1972)"
    assert first(client, "shichinin no samurai") == "Seven Samurai (1954)"
    assert first(client, "Tokyo monogatari") == "Tokyo Story (1953)"
    assert first(client, "無間道") == "Infernal Affairs (2002)"
    page = movies(client, q="ocean")
    assert len({m["id"] for m in page["items"]}) == len(page["items"])


def test_fractions_and_numbers(client: TestClient) -> None:
    assert first(client, "8 1/2") == "8½ (1963)"
    assert first(client, "8½") == "8½ (1963)"
    assert first(client, "otto e mezzo") == "8½ (1963)"
    assert first(client, "2001") == "2001: A Space Odyssey (1968)"
    assert first(client, "12 angry") == "12 Angry Men (1957)"


def test_word_prefix_and_alias(client: TestClient) -> None:
    long = "Dr. Strangelove or: How I Learned to Stop Worrying and Love the Bomb (1964)"
    assert first(client, "stop worrying") == long
    assert first(client, "dr strangelove") == long


def test_typos_only_for_longer_queries(client: TestClient) -> None:
    assert first(client, "stalkr") == "Stalker (1979)"
    assert first(client, "labyrinht") == "Pan's Labyrinth (2006)"
    assert len(movies(client, q="stalkr")["items"]) < 4
    assert movies(client, q="zq")["items"] == []


def test_punctuation_only_query_is_empty_not_invalid(client: TestClient) -> None:
    assert movies(client, q="?!") == {"items": [], "next_cursor": None, "has_more": False, "total": 0}


def test_filters(client: TestClient) -> None:
    page = movies(client, genre=["horror"], year_from="1977", year_to="1982", sort="release_desc")
    assert labels(page) == ["The Thing (1982)", "Nosferatu the Vampyre (1979)", "Suspiria (1977)"]
    assert page["total"] == 3
    both = movies(client, genre="horror,western", limit=48)
    assert all({g["slug"] for g in m["genres"]} & {"horror", "western"} for m in both["items"])
    runtime = movies(client, runtime_max="400", limit=48)
    assert "Dune: Part Three" not in [m["title"] for m in runtime["items"]]
    assert labels(movies(client, q="nosferatu", year_from="2000")) == ["Nosferatu (2024)"]


def test_exclude(client: TestClient) -> None:
    assert "Dune: Part Three" not in [m["title"] for m in movies(client, exclude="unreleased", limit=48)["items"]]
    assert movies(client, exclude="unreleased")["total"] == 42


def test_sorts(client: TestClient) -> None:
    titles = labels(movies(client, sort="title_asc", limit=48))
    assert titles[:3] == ["12 Angry Men (1957)", "2001: A Space Odyssey (1968)", "8½ (1963)"]
    assert titles.index("Suspiria (1977)") == titles.index("Suspiria (2018)") - 1
    newest = movies(client, sort="release_desc", limit=48)["items"]
    assert newest[0]["title"] == "Dune: Part Three"
    assert [m["title"] for m in newest if m["year"] == 1984] == ["Dune", "Paris, Texas"]
    oldest = movies(client, sort="release_asc", limit=48)["items"]
    assert oldest[0]["year"] == min(m["year"] for m in oldest if m["year"])
    runtimes = movies(client, sort="runtime_asc", limit=48)["items"]
    assert runtimes[-1]["title"] == "Dune: Part Three"
    known = [m["runtime_minutes"] for m in runtimes if m["runtime_minutes"] is not None]
    assert known == sorted(known)
    longest = movies(client, sort="runtime_desc", limit=48)["items"]
    assert longest[0]["runtime_minutes"] == max(known)


@pytest.mark.parametrize("sort", ["notable", "title_asc", "release_desc", "release_asc", "runtime_asc", "runtime_desc"])
def test_cursor_walks_everything_once(client: TestClient, sort: str) -> None:
    seen: list[str] = []
    sizes = []
    cursor = None
    while True:
        page = movies(client, sort=sort, limit=10, **({"cursor": cursor} if cursor else {}))
        assert page["has_more"] == (page["next_cursor"] is not None)
        seen += [m["id"] for m in page["items"]]
        sizes.append(len(page["items"]))
        cursor = page["next_cursor"]
        if not cursor:
            break
    assert len(seen) == len(set(seen)) == 43
    assert sizes == [10, 10, 10, 10, 3]


def test_cursor_walks_search_results(client: TestClient) -> None:
    all_ids = [m["id"] for m in movies(client, q="the", limit=48)["items"]]
    seen: list[str] = []
    cursor = None
    while True:
        page = movies(client, q="the", limit=3, **({"cursor": cursor} if cursor else {}))
        seen += [m["id"] for m in page["items"]]
        cursor = page["next_cursor"]
        if not cursor:
            break
    assert seen == all_ids


def test_total_only_on_first_page(client: TestClient) -> None:
    page = movies(client, limit=10)
    assert page["total"] == 43
    assert movies(client, limit=10, cursor=page["next_cursor"])["total"] is None


def test_cursor_errors(client: TestClient) -> None:
    cursor = movies(client, limit=5)["next_cursor"]
    other = client.get("/api/v1/movies", params={"limit": 5, "genre": "drama", "cursor": cursor})
    assert other.status_code == 400
    assert other.json()["error"]["code"] == "invalid_cursor"
    for bad in ("not-a-cursor", "eyJ2IjoxfQ"):
        assert client.get("/api/v1/movies", params={"cursor": bad}).status_code == 400


@pytest.mark.parametrize(
    ("params", "field"),
    [
        ({"q": "x" * 201}, "q"),
        ({"year_from": "abc"}, "year_from"),
        ({"year_from": "2000", "year_to": "1990"}, "year_to"),
        ({"runtime_max": "0"}, "runtime_max"),
        ({"limit": "49"}, "limit"),
        ({"sort": "relevance"}, "sort"),
        ({"exclude": "musicals"}, "exclude"),
    ],
)
def test_invalid_parameters(client: TestClient, params: dict[str, str], field: str) -> None:
    response = client.get("/api/v1/movies", params=params)
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "invalid_parameters"
    assert field in error["fields"]
    assert error["request_id"] == response.headers["x-request-id"]


def test_unknown_sort_is_422(client: TestClient) -> None:
    response = client.get("/api/v1/movies", params={"sort": "popular"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_parameters"


def test_movie_detail(client: TestClient) -> None:
    stalker = movies(client, q="stalker")["items"][0]
    detail = client.get(f"/api/v1/movies/{stalker['id']}").json()
    assert detail["original_title"] == "Сталкер"
    assert detail["release"] == {"status": "released", "date": None, "country": "SU"}
    assert detail["provenance"]["sources"][0]["name"] == "CineBase fixtures"
    assert detail["provenance"]["sources"][0]["external_id"] == "cbf-0035"
    # The import batch adds an alternate title without changing the film's UUID.
    assert "Stalker (Сталкер)" in [t["title"] for t in detail["alternate_titles"]]
    assert detail["runtime_minutes"] == 162


def test_credits_keep_roles(client: TestClient) -> None:
    suspiria = movies(client, q="Suspiria (2018)")["items"][0]
    credits = client.get(f"/api/v1/movies/{suspiria['id']}/credits").json()
    swinton = [c for c in credits["cast"] if c["person"]["name"] == "Tilda Swinton"]
    assert any("Mother Markos" in (c["character"] or "") for c in swinton)
    solaris = movies(client, q="Solaris (2002)")["items"][0]
    crew = client.get(f"/api/v1/movies/{solaris['id']}/credits").json()["crew"]
    soderbergh = [c["job"] for c in crew if c["person"]["name"] == "Steven Soderbergh"]
    assert soderbergh == ["Director", "Screenplay", "Director of Photography", "Editor"]


def test_not_found(client: TestClient) -> None:
    for path in (
        "/api/v1/movies/00000000-0000-0000-0000-000000000000",
        "/api/v1/movies/not-a-uuid",
        "/api/v1/movies/00000000-0000-0000-0000-000000000000/credits",
        "/api/v1/collections/nope",
        "/api/v1/people/00000000-0000-0000-0000-000000000000",
        "/nowhere",
    ):
        response = client.get(path)
        assert response.status_code == 404, path
        assert response.json()["error"]["code"].endswith("not_found")


def test_request_id_round_trip(client: TestClient) -> None:
    assert client.get("/health/live", headers={"X-Request-ID": "abc-123"}).headers["x-request-id"] == "abc-123"
    assert client.get("/health/live", headers={"X-Request-ID": "bad id!"}).headers["x-request-id"].startswith("req_")


def test_genres_collections_discover(client: TestClient) -> None:
    assert {"slug": "horror", "name": "Horror"} in client.get("/api/v1/genres").json()
    collections = client.get("/api/v1/collections").json()
    assert [c["slug"] for c in collections] == ["told-twice", "beyond-english", "under-100-minutes"]
    told = client.get("/api/v1/collections/told-twice/movies").json()
    assert labels(told)[:2] == ["Suspiria (1977)", "Suspiria (2018)"]
    discover = client.get("/api/v1/discover").json()
    assert discover["catalog"]["movie_count"] == 43
    assert len(discover["blocks"]) == 3


def test_person(client: TestClient) -> None:
    suspiria = movies(client, q="Suspiria (1977)")["items"][0]
    argento = suspiria["directors"][0]
    person = client.get(f"/api/v1/people/{argento['id']}").json()
    assert person["name"] == "Dario Argento"
    films = client.get(f"/api/v1/people/{argento['id']}/movies").json()
    assert {(f["movie"]["title"], f["job"]) for f in films["items"]} == {
        ("Suspiria", "Director"),
        ("Suspiria", "Screenplay"),
    }


def test_openapi_lists_endpoints(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/movies" in paths
    assert "/api/v1/movies/{movie_id}/credits" in paths
