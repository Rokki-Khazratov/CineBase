/**
 * Catalog DTOs. They mirror the planned `/api/v1` contract (docs/TECHNICAL_SPEC.md §5) so screens can
 * switch from FixtureCatalog to an HTTP client without changes.
 */

export type MediaSource = {
  name: string;
  kind: "synthetic" | "provider" | "local";
  attribution: string | null;
  /** Licence of a provider image, e.g. "CC BY-SA 4.0" or "Public domain". */
  license?: string | null;
  /** Page describing the file, its author and licence (e.g. the Wikimedia Commons file page). */
  url?: string | null;
};

export type Media = {
  url: string;
  alt: string;
  width: number | null;
  height: number | null;
  source: MediaSource;
};

export type GenreRef = { slug: string; name: string };
export type PersonRef = { id: string; name: string };

export type MovieSummary = {
  id: string;
  title: string;
  original_title: string | null;
  year: number | null;
  runtime_minutes: number | null;
  poster: Media | null;
  genres: GenreRef[];
  directors: PersonRef[];
  /** feature, short (40 minutes or less, or catalogued as a short) or tv (made-for-TV film). */
  kind?: MovieKind;
};

export type MovieKind = "feature" | "short" | "tv";

export type ReleaseStatus = "released" | "announced" | "unknown";

export type AlternateTitle = { title: string; locale: string | null };

export type MovieDetail = MovieSummary & {
  synopsis: string | null;
  /** Short provider description, e.g. "1979 film by Andrei Tarkovsky". */
  description?: string | null;
  backdrop: Media | null;
  original_language: string | null;
  release: {
    status: ReleaseStatus;
    /** ISO date (YYYY-MM-DD) or null when only the year is known. */
    date: string | null;
    country: string | null;
  };
  alternate_titles: AlternateTitle[];
  provenance: {
    sources: { name: string; external_id: string; url?: string | null }[];
    catalog_version: string;
  };
  links: { credits: string };
};

export type Credit = {
  person: PersonRef;
  department: string;
  job: string;
  character: string | null;
  order: number;
};

export type MovieCredits = {
  movie_id: string;
  cast: Credit[];
  crew: Credit[];
};

export type Page<T> = {
  items: T[];
  next_cursor: string | null;
  has_more: boolean;
  /** Number of matching films; only computed for the first page. */
  total?: number | null;
};

export type Collection = {
  slug: string;
  title: string;
  description: string;
  movie_count: number;
};

export type DiscoverBlock = Collection & { items: MovieSummary[] };

export type CatalogInfo = { movie_count: number; catalog_version: string; sources?: string[] };

export type Discover = {
  blocks: DiscoverBlock[];
  catalog: CatalogInfo;
};

export const SORTS = [
  "relevance",
  "notable",
  "title_asc",
  "release_desc",
  "release_asc",
  "runtime_asc",
  "runtime_desc",
] as const;
export type Sort = (typeof SORTS)[number];

/** Kinds of film a list can leave out. */
export const EXCLUSIONS = ["short", "tv", "documentary", "unreleased"] as const;
export type Exclusion = (typeof EXCLUSIONS)[number];

/** Validated `/movies` parameters. Build them with `parseMovieQuery`. */
export type MovieQuery = {
  q: string;
  genres: string[];
  year_from: number | null;
  year_to: number | null;
  runtime_max: number | null;
  exclude: Exclusion[];
  sort: Sort;
  limit: number;
  cursor: string | null;
};

export type ApiErrorBody = {
  error: {
    code: string;
    message: string;
    fields?: Record<string, string>;
    request_id: string;
  };
};

let requestCounter = 0;

/** Fixture request IDs are sequential: random values are not allowed during prerendering, and tests stay stable. */
function nextRequestId(): string {
  requestCounter += 1;
  return `req_fixture_${requestCounter.toString(36).padStart(6, "0")}`;
}

export class CatalogError extends Error {
  readonly status: number;
  readonly code: string;
  readonly fields: Record<string, string> | undefined;
  readonly requestId: string;

  constructor(status: number, code: string, message: string, fields?: Record<string, string>, requestId?: string) {
    super(message);
    this.name = "CatalogError";
    this.status = status;
    this.code = code;
    this.fields = fields;
    this.requestId = requestId ?? nextRequestId();
  }

  toJSON(): ApiErrorBody {
    return {
      error: {
        code: this.code,
        message: this.message,
        ...(this.fields ? { fields: this.fields } : {}),
        request_id: this.requestId,
      },
    };
  }
}

export type RequestOptions = { signal?: AbortSignal };

/** The only way screens read catalog data. */
export interface CatalogClient {
  listMovies(query: MovieQuery, options?: RequestOptions): Promise<Page<MovieSummary>>;
  getMovie(id: string, options?: RequestOptions): Promise<MovieDetail>;
  getCredits(id: string, options?: RequestOptions): Promise<MovieCredits>;
  listGenres(options?: RequestOptions): Promise<GenreRef[]>;
  getCatalogInfo(options?: RequestOptions): Promise<CatalogInfo>;
  getDiscover(options?: RequestOptions): Promise<Discover>;
  listCollections(options?: RequestOptions): Promise<Collection[]>;
  getCollectionMovies(slug: string, options?: RequestOptions): Promise<Page<MovieSummary>>;
}
