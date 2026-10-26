import { buildMovieQuery, catalog, type MovieDetail, type MovieSummary } from "@/catalog";
import { normalizeText } from "@/catalog/normalize";

function nameSet(movie: MovieDetail): Set<string> {
  const names = [movie.title, movie.original_title, ...movie.alternate_titles.map((a) => a.title)];
  return new Set(names.filter((n): n is string => !!n).map(normalizeText).filter(Boolean));
}

/**
 * Other films that share one of this film's titles: remakes, re-adaptations, or unrelated films with the
 * same name. Uses the normal search, then keeps only exact title matches so near misses are not listed.
 */
export async function otherVersions(movie: MovieDetail): Promise<MovieSummary[]> {
  const mine = nameSet(movie);
  const candidates = new Map<string, MovieSummary>();
  for (const q of new Set([movie.title, movie.original_title].filter((t): t is string => !!t))) {
    const page = await catalog.listMovies(buildMovieQuery({ q, limit: 48 }));
    page.items.forEach((m) => candidates.set(m.id, m));
  }
  const matches: MovieSummary[] = [];
  for (const candidate of candidates.values()) {
    if (candidate.id === movie.id) continue;
    const detail = await catalog.getMovie(candidate.id);
    if ([...nameSet(detail)].some((n) => mine.has(n))) matches.push(candidate);
  }
  return matches.sort((a, b) => (a.year ?? 9999) - (b.year ?? 9999));
}
