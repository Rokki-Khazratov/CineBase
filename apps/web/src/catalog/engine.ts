/**
 * In-memory catalog built from fixture data: DTO mapping, search ranking, filters, sorts and keyset paging.
 * The rules follow docs/TECHNICAL_SPEC.md §5–§6 so the fixture prototype behaves like the future API.
 */
import { CATALOG_VERSION, type FixtureData, type RawMovie } from "./fixture-data";
import { bestSimilarity, normalizeText, parseTitleYear, trigrams } from "./normalize";
import { decodeCursor, encodeCursor, type SortKey } from "./query";
import {
  CatalogError,
  type Collection,
  type Credit,
  type GenreRef,
  type Media,
  type MovieCredits,
  type MovieDetail,
  type MovieQuery,
  type MovieSummary,
  type Page,
  type PersonRef,
} from "./types";

export const POSTER_BASE_URL = "/fixture-art/";
const SIMILARITY_THRESHOLD = 0.3;
const FUZZY_MIN_LENGTH = 4;
const SUBSTRING_MIN_LENGTH = 3;

type NameKind = 0 | 1 | 2; // title, original title, alternate title

type SearchName = { norm: string; grams: Set<string>; kind: NameKind };

type MovieRecord = {
  raw: RawMovie;
  summary: MovieSummary;
  detail: MovieDetail;
  credits: MovieCredits;
  names: SearchName[];
  titleKey: string;
};

type Direction = 1 | -1;

/** Match tiers, best first. */
export const Tier = { Exact: 0, Prefix: 1, WordPrefix: 2, Substring: 3, Similar: 4 } as const;

export type MatchInfo = { tier: number; score: number; kind: NameKind };

function compareParts(a: string | number, b: string | number): number {
  if (typeof a === "number" && typeof b === "number") return a - b;
  const sa = String(a);
  const sb = String(b);
  return sa < sb ? -1 : sa > sb ? 1 : 0;
}

function compareKeys(a: SortKey, b: SortKey, directions: Direction[]): number {
  for (let i = 0; i < a.length; i++) {
    const c = compareParts(a[i], b[i]) * (directions[i] ?? 1);
    if (c !== 0) return c;
  }
  return 0;
}

export class FixtureEngine {
  readonly version = CATALOG_VERSION;
  private readonly records: MovieRecord[];
  private readonly byId = new Map<string, MovieRecord>();
  private readonly bySlug = new Map<string, MovieRecord>();
  private readonly genres: GenreRef[];
  private readonly collections: FixtureData["collections"];

  constructor(data: FixtureData) {
    const people = new Map(data.people.map((p) => [p.slug, p]));
    const genres = new Map(data.genres.map((g) => [g.slug, g]));
    this.genres = data.genres.map(({ slug, name }) => ({ slug, name }));
    this.collections = data.collections;

    const personRef = (slug: string): PersonRef => {
      const person = people.get(slug);
      if (!person) throw new Error(`Unknown person ${slug}`);
      return { id: person.id, name: person.name };
    };

    this.records = data.movies.map((raw) => {
      const credits: Credit[] = raw.credits.map((c) => ({
        person: personRef(c.person),
        department: c.department,
        job: c.job,
        character: c.character,
        order: c.order,
      }));
      const directors: PersonRef[] = [];
      for (const c of credits) {
        if (c.department === "Directing" && c.job === "Director" && !directors.some((d) => d.id === c.person.id)) {
          directors.push(c.person);
        }
      }
      const poster: Media | null = raw.poster
        ? {
            url: POSTER_BASE_URL + raw.poster.file,
            alt: `Illustrative poster for ${raw.title}${raw.release_year ? ` (${raw.release_year})` : ""}`,
            width: 400,
            height: 600,
            source: {
              name: "CineBase generated art",
              kind: "synthetic",
              attribution: "Generated placeholder, not the film's official artwork",
            },
          }
        : null;
      const summary: MovieSummary = {
        id: raw.id,
        title: raw.title,
        original_title: raw.original_title,
        year: raw.release_year,
        runtime_minutes: raw.runtime_minutes,
        poster,
        genres: raw.genres.map((slug) => {
          const genre = genres.get(slug);
          if (!genre) throw new Error(`Unknown genre ${slug}`);
          return { slug: genre.slug, name: genre.name };
        }),
        directors,
        kind: "feature",
      };
      const detail: MovieDetail = {
        ...summary,
        synopsis: raw.synopsis,
        description: null,
        backdrop: null,
        original_language: raw.original_language,
        release: { status: raw.status, date: raw.release_date, country: raw.release_country },
        alternate_titles: raw.alternate_titles,
        provenance: {
          sources: raw.external_ids.map((e) => ({ name: e.provider, external_id: e.external_id })),
          catalog_version: CATALOG_VERSION,
        },
        links: { credits: `/api/v1/movies/${raw.id}/credits` },
      };
      const byOrder = (a: Credit, b: Credit) => a.order - b.order;
      const movieCredits: MovieCredits = {
        movie_id: raw.id,
        cast: credits.filter((c) => c.department === "Acting").sort(byOrder),
        crew: credits.filter((c) => c.department !== "Acting").sort(byOrder),
      };

      const names: SearchName[] = [];
      const addName = (text: string | null, kind: NameKind) => {
        if (!text) return;
        const norm = normalizeText(text);
        if (norm && !names.some((n) => n.norm === norm)) names.push({ norm, grams: trigrams(norm), kind });
      };
      addName(raw.title, 0);
      addName(raw.original_title, 1);
      raw.alternate_titles.forEach((a) => addName(a.title, 2));

      return { raw, summary, detail, credits: movieCredits, names, titleKey: normalizeText(raw.title) };
    });

    for (const r of this.records) {
      if (this.byId.has(r.raw.id)) throw new Error(`Duplicate movie id ${r.raw.id}`);
      this.byId.set(r.raw.id, r);
      this.bySlug.set(r.raw.slug, r);
    }
  }

  get movieCount(): number {
    return this.records.length;
  }

  allIds(): string[] {
    return this.records.map((r) => r.raw.id);
  }

  listGenres(): GenreRef[] {
    return this.genres.map((g) => ({ ...g }));
  }

  /** Best match of a normalized query against one film's titles and aliases, or null. */
  match(record: MovieRecord, query: string, queryGrams: Set<string>): MatchInfo | null {
    let best: MatchInfo | null = null;
    const consider = (m: MatchInfo) => {
      if (!best || m.tier < best.tier || (m.tier === best.tier && (m.score > best.score || (m.score === best.score && m.kind < best.kind)))) {
        best = m;
      }
    };
    for (const name of record.names) {
      if (name.norm === query) consider({ tier: Tier.Exact, score: 1, kind: name.kind });
      else if (name.norm.startsWith(query)) consider({ tier: Tier.Prefix, score: query.length / name.norm.length, kind: name.kind });
      else if (name.norm.includes(` ${query}`)) consider({ tier: Tier.WordPrefix, score: query.length / name.norm.length, kind: name.kind });
      else if (query.length >= SUBSTRING_MIN_LENGTH && name.norm.includes(query)) {
        consider({ tier: Tier.Substring, score: query.length / name.norm.length, kind: name.kind });
      } else if (query.length >= FUZZY_MIN_LENGTH) {
        const sim = bestSimilarity(query, queryGrams, name.norm);
        if (sim >= SIMILARITY_THRESHOLD) consider({ tier: Tier.Similar, score: sim, kind: name.kind });
      }
    }
    return best;
  }

  private passesFilters(r: MovieRecord, q: MovieQuery): boolean {
    const year = r.raw.release_year;
    if (q.genres.length > 0 && !q.genres.some((g) => r.raw.genres.includes(g))) return false;
    if (q.year_from !== null && (year === null || year < q.year_from)) return false;
    if (q.year_to !== null && (year === null || year > q.year_to)) return false;
    if (q.runtime_max !== null && (r.raw.runtime_minutes === null || r.raw.runtime_minutes > q.runtime_max)) return false;
    if (q.exclude.includes("short") && r.summary.kind === "short") return false;
    if (q.exclude.includes("tv") && r.summary.kind === "tv") return false;
    if (q.exclude.includes("documentary") && r.raw.genres.includes("documentary")) return false;
    if (q.exclude.includes("unreleased") && r.raw.status === "announced") return false;
    return true;
  }

  /**
   * Sort key for every supported order. Each key ends with the UUID as a tie-breaker, and missing values
   * get an explicit flag so they always land at the end of the list.
   */
  private sortKey(r: MovieRecord, query: MovieQuery, matchInfo: MatchInfo | null, wantedYear: number | null): {
    key: SortKey;
    dirs: Direction[];
  } {
    const year = r.raw.release_year;
    const runtime = r.raw.runtime_minutes;
    // Known full dates sort before year-only dates in the same year; an unknown day is never invented.
    const release = r.raw.release_date ?? (year !== null ? String(year) : "");
    switch (query.sort) {
      case "relevance": {
        const m = matchInfo ?? { tier: 9, score: 0, kind: 2 };
        const yearMiss = wantedYear !== null && year !== wantedYear ? 1 : 0;
        return {
          // Within a tier, a match on the display title beats one on an original or alternate title.
          key: [yearMiss, m.tier, m.kind, Math.round(m.score * 1e6), year === null ? 1 : 0, year ?? 0, r.titleKey, r.raw.id],
          dirs: [1, 1, 1, -1, 1, -1, 1, 1],
        };
      }
      case "notable":
        // Fixtures carry no coverage data, so every film ties on notability and newer films come first.
        return { key: [0, year === null ? 1 : 0, year ?? 0, r.titleKey, r.raw.id], dirs: [-1, 1, -1, 1, 1] };
      case "title_asc":
        return { key: [r.titleKey, year === null ? 1 : 0, year ?? 0, r.raw.id], dirs: [1, 1, 1, 1] };
      case "release_desc":
      case "release_asc":
        return { key: [release ? 0 : 1, release, r.titleKey, r.raw.id], dirs: [1, query.sort === "release_desc" ? -1 : 1, 1, 1] };
      case "runtime_asc":
      case "runtime_desc":
        return {
          key: [runtime === null ? 1 : 0, runtime ?? 0, r.titleKey, r.raw.id],
          dirs: [1, query.sort === "runtime_desc" ? -1 : 1, 1, 1],
        };
    }
  }

  /** Runs a validated query. Throws 400 for a cursor that does not belong to this query or catalog version. */
  listMovies(query: MovieQuery): Page<MovieSummary> {
    const { text, year } = parseTitleYear(query.q);
    const normalized = normalizeText(text);
    const grams = trigrams(normalized);
    if (query.q && !normalized) {
      // Only punctuation: nothing can match, but it is not an invalid request.
      return { items: [], next_cursor: null, has_more: false, total: query.cursor ? null : 0 };
    }

    const rows: { record: MovieRecord; key: SortKey }[] = [];
    let dirs: Direction[] = [];
    for (const record of this.records) {
      if (!this.passesFilters(record, query)) continue;
      let matchInfo: MatchInfo | null = null;
      if (normalized) {
        matchInfo = this.match(record, normalized, grams);
        if (!matchInfo) continue;
      }
      const sk = this.sortKey(record, query, matchInfo, year);
      dirs = sk.dirs;
      rows.push({ record, key: sk.key });
    }
    rows.sort((a, b) => compareKeys(a.key, b.key, dirs));

    let start = 0;
    if (query.cursor) {
      const after = decodeCursor(query.cursor, query, this.version);
      start = rows.findIndex((row) => compareKeys(row.key, after, dirs) > 0);
      if (start === -1) start = rows.length;
    }
    const slice = rows.slice(start, start + query.limit);
    const hasMore = start + query.limit < rows.length;
    return {
      items: slice.map((row) => row.record.summary),
      next_cursor: hasMore ? encodeCursor(query, this.version, slice[slice.length - 1].key) : null,
      has_more: hasMore,
      total: query.cursor ? null : rows.length,
    };
  }

  private require(id: string): MovieRecord {
    const record = this.byId.get(id);
    if (!record) throw new CatalogError(404, "movie_not_found", "No film with this ID exists in the catalog.");
    return record;
  }

  getMovie(id: string): MovieDetail {
    return this.require(id).detail;
  }

  getCredits(id: string): MovieCredits {
    return this.require(id).credits;
  }

  listCollections(): Collection[] {
    return this.collections.map((c) => ({
      slug: c.slug,
      title: c.title,
      description: c.description,
      movie_count: c.movies.length,
    }));
  }

  getCollectionMovies(slug: string): Page<MovieSummary> {
    const collection = this.collections.find((c) => c.slug === slug);
    if (!collection) throw new CatalogError(404, "collection_not_found", "No collection with this slug exists.");
    const items = collection.movies.map((s) => {
      const record = this.bySlug.get(s);
      if (!record) throw new Error(`Collection ${slug} references unknown movie ${s}`);
      return record.summary;
    });
    return { items, next_cursor: null, has_more: false };
  }
}
