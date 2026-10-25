/**
 * Catalog DTOs. They mirror the planned `/api/v1` contract (docs/TECHNICAL_SPEC.md §5) so screens can
 * switch from FixtureCatalog to an HTTP client without changes.
 */

export type MediaSource = {
  name: string;
  kind: "synthetic" | "provider" | "local";
  attribution: string | null;
};

export type Media = {
  url: string;
  alt: string;
  width: number;
  height: number;
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
};

export type ReleaseStatus = "released" | "announced";

export type AlternateTitle = { title: string; locale: string | null };

export type MovieDetail = MovieSummary & {
  synopsis: string | null;
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
    sources: { name: string; external_id: string }[];
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
};

export type Collection = {
  slug: string;
  title: string;
  description: string;
  movie_count: number;
};

export type DiscoverBlock = Collection & { items: MovieSummary[] };

export type Discover = {
  blocks: DiscoverBlock[];
  catalog: { movie_count: number; catalog_version: string };
};

export const SORTS = ["relevance", "title_asc", "release_desc", "runtime_asc"] as const;
export type Sort = (typeof SORTS)[number];

/** Validated `/movies` parameters. Build them with `parseMovieQuery`. */
export type MovieQuery = {
  q: string;
  genres: string[];
  year_from: number | null;
  year_to: number | null;
  runtime_max: number | null;
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
    this.requestId = requestId ?? `req_${Math.random().toString(36).slice(2, 10)}`;
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
  getDiscover(options?: RequestOptions): Promise<Discover>;
  listCollections(options?: RequestOptions): Promise<Collection[]>;
  getCollectionMovies(slug: string, options?: RequestOptions): Promise<Page<MovieSummary>>;
}
