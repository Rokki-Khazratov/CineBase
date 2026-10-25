/** Text normalization and similarity used by catalog search (docs/TECHNICAL_SPEC.md §6). */

const LETTER_MAP: Record<string, string> = {
  ß: "ss",
  æ: "ae",
  ø: "o",
  œ: "oe",
  ł: "l",
  đ: "d",
  ð: "d",
  þ: "th",
  ı: "i",
};

/**
 * Case-, accent- and punctuation-insensitive search key.
 * "Amélie" → "amelie", "Ocean's 11" → "oceans 11", "8½" → "8 1/2" (via NFKD), "Dr. Strangelove" → "dr strangelove".
 */
export function normalizeText(input: string): string {
  let s = input.normalize("NFKD").replace(/[̀-ͯ]/g, "");
  s = s.normalize("NFC").toLowerCase();
  s = s.replace(/[ßæøœłđðþı]/g, (ch) => LETTER_MAP[ch] ?? ch);
  // NFKD turns ½ into "1⁄2" with a fraction slash; keep it readable as "1/2".
  s = s.replace(/⁄/g, "/");
  s = s.replace(/['’‘`´ʼ]/g, "");
  s = s.replace(/[^\p{L}\p{N}/]+/gu, " ");
  // "8 1/2" and "8½" (→ "81/2") should meet: put a space before a fraction glued to a number.
  s = s.replace(/(\d)(\d\/\d)/g, "$1 $2");
  return s.replace(/\s+/g, " ").trim();
}

const TITLE_YEAR = /^(.*\S)\s*\((\d{4})\)\s*$/u;

/** Recognizes the explicitly supported "Title (YYYY)" form. Other numbers stay part of the title. */
export function parseTitleYear(raw: string): { text: string; year: number | null } {
  const match = TITLE_YEAR.exec(raw.trim());
  if (!match) return { text: raw.trim(), year: null };
  return { text: match[1], year: Number(match[2]) };
}

/** pg_trgm-style trigrams: each word is padded with two leading spaces and one trailing space. */
export function trigrams(normalized: string): Set<string> {
  const out = new Set<string>();
  for (const word of normalized.split(" ")) {
    if (!word) continue;
    const padded = `  ${word} `;
    const chars = Array.from(padded);
    for (let i = 0; i + 3 <= chars.length; i++) out.add(chars.slice(i, i + 3).join(""));
  }
  return out;
}

export function similarity(a: Set<string>, b: Set<string>): number {
  if (a.size === 0 || b.size === 0) return 0;
  let shared = 0;
  for (const t of a) if (b.has(t)) shared++;
  return shared / (a.size + b.size - shared);
}

/**
 * Best similarity between the query and either the whole name or any run of consecutive words of the
 * same length as the query, so "stalkr" still matches the word "stalker" inside a longer title.
 */
export function bestSimilarity(query: string, queryGrams: Set<string>, name: string): number {
  let best = similarity(queryGrams, trigrams(name));
  const qWords = query.split(" ").length;
  const words = name.split(" ");
  if (words.length > qWords) {
    for (let i = 0; i + qWords <= words.length; i++) {
      best = Math.max(best, similarity(queryGrams, trigrams(words.slice(i, i + qWords).join(" "))));
    }
  }
  return best;
}
