/**
 * URL ⇄ query helpers for the results page. The API parser is strict (422 on bad input); the page is
 * forgiving instead: a hand-edited or stale URL drops the values it cannot use rather than showing an error.
 */
import { buildMovieQuery, defaultSort, EXCLUSIONS, MAX_QUERY_LENGTH, SORTS, toSearchParams, type Exclusion, type MovieQuery, type Sort } from "@/catalog";

export const DECADES = [2020, 2010, 2000, 1990, 1980, 1970, 1960, 1950, 1940, 1930, 1920, 1910, 1900, 1890] as const;
export const RUNTIME_PRESETS = [90, 120, 150] as const;

export const SORT_LABELS: Record<Sort, string> = {
  relevance: "Best match",
  notable: "Best known",
  release_desc: "Newest first",
  release_asc: "Oldest first",
  title_asc: "Title A–Z",
  runtime_asc: "Shortest first",
  runtime_desc: "Longest first",
};

/** Sort options in menu order; "Best match" only while there is a search term. */
export function sortOptions(q: string): Sort[] {
  const browse: Sort[] = ["notable", "release_desc", "release_asc", "title_asc", "runtime_asc", "runtime_desc"];
  return q ? ["relevance", ...browse] : browse;
}

export const EXCLUSION_LABELS: Record<Exclusion, string> = {
  short: "Short films",
  tv: "TV films",
  documentary: "Documentaries",
  unreleased: "Unreleased films",
};

/**
 * Development-only switches that never become part of the canonical query. `_fail=1` makes every request
 * fail; `_fail=once` fails until the first "Try again", to show recovery.
 */
export type DevOptions = { latencyMs: number | undefined; fail: "always" | "once" | null };

function intParam(params: URLSearchParams, key: string): number | null {
  const raw = params.get(key);
  if (!raw || !/^\d{1,4}$/.test(raw)) return null;
  return Number(raw);
}

export function queryFromUrl(params: URLSearchParams, genreSlugs: ReadonlySet<string>): MovieQuery {
  const q = (params.get("q") ?? "").trim().slice(0, MAX_QUERY_LENGTH);
  const genres = [...new Set(params.getAll("genre"))].filter((g) => genreSlugs.has(g)).sort();
  let yearFrom = intParam(params, "year_from");
  let yearTo = intParam(params, "year_to");
  if (yearFrom !== null && yearTo !== null && yearFrom > yearTo) [yearFrom, yearTo] = [yearTo, yearFrom];
  const runtime = intParam(params, "runtime_max");
  const exclude = [...new Set(params.getAll("exclude").flatMap((v) => v.split(",")))]
    .filter((v): v is Exclusion => (EXCLUSIONS as readonly string[]).includes(v))
    .sort();
  const rawSort = params.get("sort");
  let sort: Sort = defaultSort(q);
  if (rawSort && (SORTS as readonly string[]).includes(rawSort) && !(rawSort === "relevance" && !q)) {
    sort = rawSort as Sort;
  }
  return buildMovieQuery({
    q,
    genres,
    year_from: yearFrom,
    year_to: yearTo,
    runtime_max: runtime && runtime > 0 ? runtime : null,
    exclude,
    sort,
  });
}

export function devOptionsFromUrl(params: URLSearchParams): DevOptions {
  const latency = params.get("_latency");
  return {
    latencyMs: latency && /^\d{1,5}$/.test(latency) ? Number(latency) : undefined,
    fail: params.get("_fail") === "1" ? "always" : params.get("_fail") === "once" ? "once" : null,
  };
}

/** Applies a change and keeps the sort sensible: "Best match" only exists while there is a search term. */
export function withChanges(query: MovieQuery, changes: Partial<MovieQuery>): MovieQuery {
  const next = { ...query, ...changes, cursor: null };
  next.q = next.q.trim();
  if (changes.q !== undefined && changes.sort === undefined) {
    const wasDefault = query.sort === defaultSort(query.q);
    if (wasDefault || (next.sort === "relevance" && !next.q)) next.sort = defaultSort(next.q);
  }
  return next;
}

export function resultsHref(query: MovieQuery): string {
  const qs = toSearchParams(query).toString();
  return qs ? `/movies?${qs}` : "/movies";
}

export function hasActiveFilters(query: MovieQuery): boolean {
  return (
    query.genres.length > 0 ||
    query.year_from !== null ||
    query.year_to !== null ||
    query.runtime_max !== null ||
    query.exclude.length > 0
  );
}

/** The change that clears every filter but keeps the search term and sort. */
export const NO_FILTERS: Partial<MovieQuery> = { genres: [], year_from: null, year_to: null, runtime_max: null, exclude: [] };

export function decadeValue(query: MovieQuery): string {
  const { year_from: from, year_to: to } = query;
  if (from === null && to === null) return "";
  const decade = DECADES.find((d) => {
    const range = decadeRange(d);
    return range.year_from === from && range.year_to === to;
  });
  return decade === undefined ? "custom" : String(decade);
}

export function yearRangeLabel(from: number | null, to: number | null): string {
  if (from !== null && to !== null) return from === to ? String(from) : `${from}–${to}`;
  if (from !== null) return `${from} or later`;
  return `${to} or earlier`;
}

export function decadeLabel(decade: number): string {
  return decade === 1890 ? "Before 1900" : `${decade}s`;
}

export function decadeRange(decade: number): { year_from: number; year_to: number } {
  return decade === 1890 ? { year_from: 1870, year_to: 1899 } : { year_from: decade, year_to: decade + 9 };
}

/** Keeps the development switches (`_latency`, `_fail`) on URLs the page writes itself. */
export function withDevParams(href: string, dev: DevOptions): string {
  const extra = new URLSearchParams();
  if (dev.latencyMs !== undefined) extra.set("_latency", String(dev.latencyMs));
  if (dev.fail) extra.set("_fail", dev.fail === "always" ? "1" : "once");
  const qs = extra.toString();
  if (!qs) return href;
  return href + (href.includes("?") ? "&" : "?") + qs;
}
