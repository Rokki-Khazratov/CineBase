/** `/movies` parameter parsing, canonical URLs and opaque cursors. */
import { CatalogError, SORTS, type MovieQuery, type Sort } from "./types";

export const MAX_QUERY_LENGTH = 200;
export const DEFAULT_LIMIT = 24;
export const MAX_LIMIT = 48;

type ParamSource = URLSearchParams | Record<string, string | string[] | undefined>;

function all(source: ParamSource, key: string): string[] {
  if (source instanceof URLSearchParams) return source.getAll(key);
  const value = source[key];
  if (value === undefined) return [];
  return Array.isArray(value) ? value : [value];
}

function first(source: ParamSource, key: string): string | undefined {
  return all(source, key)[0];
}

export function defaultSort(q: string): Sort {
  return q ? "relevance" : "release_desc";
}

function parseInteger(raw: string | undefined, field: string, errors: Record<string, string>): number | null {
  if (raw === undefined || raw === "") return null;
  if (!/^-?\d+$/.test(raw.trim())) {
    errors[field] = "Must be a whole number.";
    return null;
  }
  return Number(raw);
}

/**
 * Strict parser with the API's semantics: invalid values raise a 422 CatalogError listing every bad field.
 */
export function parseMovieQuery(source: ParamSource): MovieQuery {
  const errors: Record<string, string> = {};
  const q = (first(source, "q") ?? "").trim();
  if (q.length > MAX_QUERY_LENGTH) errors.q = `Must be at most ${MAX_QUERY_LENGTH} characters.`;

  const genres = [...new Set(all(source, "genre").flatMap((g) => g.split(",")).map((g) => g.trim()).filter(Boolean))];

  const yearFrom = parseInteger(first(source, "year_from"), "year_from", errors);
  const yearTo = parseInteger(first(source, "year_to"), "year_to", errors);
  if (yearFrom !== null && yearTo !== null && yearFrom > yearTo) {
    errors.year_to = "Must be greater than or equal to year_from.";
  }

  const runtimeMax = parseInteger(first(source, "runtime_max"), "runtime_max", errors);
  if (runtimeMax !== null && runtimeMax <= 0) errors.runtime_max = "Must be a positive number of minutes.";

  const rawSort = first(source, "sort");
  let sort: Sort = defaultSort(q);
  if (rawSort) {
    if ((SORTS as readonly string[]).includes(rawSort)) sort = rawSort as Sort;
    else errors.sort = `Must be one of: ${SORTS.join(", ")}.`;
  }
  if (sort === "relevance" && !q) errors.sort = "relevance requires a non-empty q.";

  const limit = parseInteger(first(source, "limit"), "limit", errors) ?? DEFAULT_LIMIT;
  if (limit < 1 || limit > MAX_LIMIT) errors.limit = `Must be between 1 and ${MAX_LIMIT}.`;

  if (Object.keys(errors).length > 0) {
    throw new CatalogError(422, "invalid_parameters", "Some search parameters are invalid.", errors);
  }
  return {
    q,
    genres,
    year_from: yearFrom,
    year_to: yearTo,
    runtime_max: runtimeMax,
    sort,
    limit,
    cursor: first(source, "cursor") || null,
  };
}

export function buildMovieQuery(partial: Partial<MovieQuery> = {}): MovieQuery {
  const q = (partial.q ?? "").trim();
  return {
    q,
    genres: partial.genres ?? [],
    year_from: partial.year_from ?? null,
    year_to: partial.year_to ?? null,
    runtime_max: partial.runtime_max ?? null,
    sort: partial.sort ?? defaultSort(q),
    limit: partial.limit ?? DEFAULT_LIMIT,
    cursor: partial.cursor ?? null,
  };
}

/** Canonical URL parameters: defaults are omitted, genres are sorted, cursor and limit are excluded. */
export function toSearchParams(query: MovieQuery): URLSearchParams {
  const params = new URLSearchParams();
  if (query.q) params.set("q", query.q);
  for (const g of [...query.genres].sort()) params.append("genre", g);
  if (query.year_from !== null) params.set("year_from", String(query.year_from));
  if (query.year_to !== null) params.set("year_to", String(query.year_to));
  if (query.runtime_max !== null) params.set("runtime_max", String(query.runtime_max));
  if (query.sort !== defaultSort(query.q)) params.set("sort", query.sort);
  return params;
}

/** Stable identity of a result list: everything that changes which films appear and in what order. */
export function queryKey(query: MovieQuery): string {
  return `${toSearchParams(query).toString()}|sort=${query.sort}`;
}

// --- cursors --------------------------------------------------------------------------------------

export type SortKey = (string | number)[];

type CursorPayload = { v: 1; f: string; cv: string; k: SortKey };

function fnv1a(text: string): string {
  let h = 0x811c9dc5;
  for (let i = 0; i < text.length; i++) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return (h >>> 0).toString(16).padStart(8, "0");
}

function toBase64Url(text: string): string {
  const bytes = new TextEncoder().encode(text);
  let binary = "";
  bytes.forEach((b) => (binary += String.fromCharCode(b)));
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function fromBase64Url(token: string): string {
  const padded = token.replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(token.length / 4) * 4, "=");
  const binary = atob(padded);
  return new TextDecoder().decode(Uint8Array.from(binary, (c) => c.charCodeAt(0)));
}

/** The cursor carries the full sort key of the last returned item (keyset pagination). */
export function encodeCursor(query: MovieQuery, catalogVersion: string, lastKey: SortKey): string {
  const payload: CursorPayload = { v: 1, f: fnv1a(queryKey(query)), cv: catalogVersion, k: lastKey };
  return toBase64Url(JSON.stringify(payload));
}

export function decodeCursor(token: string, query: MovieQuery, catalogVersion: string): SortKey {
  const invalid = () => new CatalogError(400, "invalid_cursor", "This page link is no longer valid. Start the list again.");
  let payload: CursorPayload;
  try {
    payload = JSON.parse(fromBase64Url(token));
  } catch {
    throw invalid();
  }
  if (
    !payload ||
    payload.v !== 1 ||
    payload.f !== fnv1a(queryKey(query)) ||
    payload.cv !== catalogVersion ||
    !Array.isArray(payload.k) ||
    !payload.k.every((part) => typeof part === "string" || typeof part === "number")
  ) {
    throw invalid();
  }
  return payload.k;
}
