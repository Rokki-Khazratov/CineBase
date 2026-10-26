import pytest

from cinebase_api.normalize import normalize_text, parse_title_year

# Same cases as apps/web/src/catalog/normalize.test.ts: both implementations must produce the same keys.
CASES = [
    ("Amélie", "amelie"),
    ("  SUSPIRIA  ", "suspiria"),
    ("Ocean's 11", "oceans 11"),
    ("Ocean’s Eleven", "oceans eleven"),
    ("Dr. Strangelove or: How I Learned", "dr strangelove or how i learned"),
    ("Paris, Texas", "paris texas"),
    ("Låt den rätte komma in", "lat den ratte komma in"),
    ("Tōkyō monogatari", "tokyo monogatari"),
    ("Stanisław Lem", "stanislaw lem"),
    ("Straße", "strasse"),
    ("8½", "8 1/2"),
    ("8 1/2", "8 1/2"),
    ("2001: A Space Odyssey", "2001 a space odyssey"),
    ("Солярис", "солярис"),
    ("七人の侍", "七人の侍"),
]


@pytest.mark.parametrize(("raw", "expected"), CASES)
def test_normalize_matches_web(raw: str, expected: str) -> None:
    assert normalize_text(raw) == expected


def test_punctuation_only_is_empty() -> None:
    assert normalize_text("?!…") == ""


def test_title_year() -> None:
    assert parse_title_year("Suspiria (1977)") == ("Suspiria", 1977)
    assert parse_title_year("2001: A Space Odyssey") == ("2001: A Space Odyssey", None)
    assert parse_title_year("Blade Runner 2049") == ("Blade Runner 2049", None)
