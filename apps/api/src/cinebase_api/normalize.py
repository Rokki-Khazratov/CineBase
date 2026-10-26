"""Search keys. Must stay identical to apps/web/src/catalog/normalize.ts (tests compare both on shared cases)."""

import re
import unicodedata

_LETTER_MAP = {"ß": "ss", "æ": "ae", "ø": "o", "œ": "oe", "ł": "l", "đ": "d", "ð": "d", "þ": "th", "ı": "i"}
_COMBINING = re.compile("[̀-ͯ]")
_APOSTROPHES = re.compile("['’‘`´ʼ]")
_DIGIT_FRACTION = re.compile(r"(\d)(\d/\d)")
_SPACES = re.compile(r"\s+")
_TITLE_YEAR = re.compile(r"^(.*\S)\s*\((\d{4})\)\s*$", re.DOTALL)


def _is_kept(ch: str) -> bool:
    return ch == "/" or unicodedata.category(ch)[0] in ("L", "N")


def normalize_text(value: str) -> str:
    """Case-, accent- and punctuation-insensitive key: "Amélie" → "amelie", "8½" → "8 1/2"."""
    s = _COMBINING.sub("", unicodedata.normalize("NFKD", value))
    s = unicodedata.normalize("NFC", s).lower()
    s = "".join(_LETTER_MAP.get(ch, ch) for ch in s)
    s = s.replace("⁄", "/")
    s = _APOSTROPHES.sub("", s)
    s = "".join(ch if _is_kept(ch) else " " for ch in s)
    s = _DIGIT_FRACTION.sub(r"\1 \2", s)
    return _SPACES.sub(" ", s).strip()


def parse_title_year(raw: str) -> tuple[str, int | None]:
    """The explicitly supported "Title (YYYY)" form. Other numbers stay part of the title."""
    match = _TITLE_YEAR.match(raw.strip())
    if not match:
        return raw.strip(), None
    return match.group(1), int(match.group(2))
