import { cacheLife } from "next/cache";
import { buildMovieQuery, catalog, type MovieDetail, type MovieSummary } from "@/catalog";
import { normalizeText } from "@/catalog/normalize";

/** Detail lookups allowed per film page, for candidates whose own titles do not match. */
const MAX_DETAIL_LOOKUPS = 6;

function normalized(names: (string | null | undefined)[]): Set<string> {
  return new Set(names.filter((n): n is string => !!n).map(normalizeText).filter(Boolean));
}

const overlaps = (a: Set<string>, b: Set<string>) => [...a].some((n) => b.has(n));

/**
 * Other films that share one of this film's titles: remakes, re-adaptations, or unrelated films with the
 * same name. Uses the normal search, then keeps only exact title matches so near misses are not listed.
 * Candidates are first compared by their main and original titles; only the few best-ranked remaining ones
 * are opened to compare their other known titles, so a large catalog costs a bounded number of requests.
 */
export async function otherVersions(movie: MovieDetail): Promise<MovieSummary[]> {
  "use cache";
  cacheLife("hours");
  const mine = normalized([movie.title, movie.original_title, ...movie.alternate_titles.map((a) => a.title)]);
  const candidates = new Map<string, MovieSummary>();
  for (const q of new Set([movie.title, movie.original_title].filter((t): t is string => !!t))) {
    const page = await catalog.listMovies(buildMovieQuery({ q, limit: 24 }));
    page.items.forEach((m) => m.id !== movie.id && candidates.set(m.id, m));
  }

  const matches: MovieSummary[] = [];
  const unsure: MovieSummary[] = [];
  for (const candidate of candidates.values()) {
    if (overlaps(normalized([candidate.title, candidate.original_title]), mine)) matches.push(candidate);
    else unsure.push(candidate);
  }
  const details = await Promise.all(unsure.slice(0, MAX_DETAIL_LOOKUPS).map((m) => catalog.getMovie(m.id).catch(() => null)));
  details.forEach((detail, i) => {
    if (detail && overlaps(normalized(detail.alternate_titles.map((a) => a.title)), mine)) matches.push(unsure[i]);
  });
  return matches.sort((a, b) => (a.year ?? 9999) - (b.year ?? 9999));
}
