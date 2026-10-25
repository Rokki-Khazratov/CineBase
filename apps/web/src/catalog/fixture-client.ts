import type { FixtureEngine } from "./engine";
import { parseMovieQuery, toSearchParams } from "./query";
import {
  CatalogError,
  type CatalogClient,
  type Collection,
  type Discover,
  type GenreRef,
  type MovieCredits,
  type MovieDetail,
  type MovieQuery,
  type MovieSummary,
  type Page,
  type RequestOptions,
} from "./types";

export type FixtureCatalogOptions = {
  /** Simulated network latency for list requests, in ms. */
  latencyMs?: number;
  /** When true every request fails with a 503, to exercise error states. */
  fail?: boolean;
};

function abortError(): DOMException {
  return new DOMException("The request was aborted.", "AbortError");
}

function wait(ms: number, signal?: AbortSignal): Promise<void> {
  if (signal?.aborted) return Promise.reject(abortError());
  if (ms <= 0) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      signal?.removeEventListener("abort", onAbort);
      resolve();
    }, ms);
    const onAbort = () => {
      clearTimeout(timer);
      reject(abortError());
    };
    signal?.addEventListener("abort", onAbort, { once: true });
  });
}

/** CatalogClient backed by bundled fixtures. Behaves like the planned HTTP API, including its errors. */
export class FixtureCatalog implements CatalogClient {
  constructor(
    private readonly engine: FixtureEngine,
    private readonly options: FixtureCatalogOptions = {},
  ) {}

  withOptions(options: FixtureCatalogOptions): FixtureCatalog {
    return new FixtureCatalog(this.engine, { ...this.options, ...options });
  }

  private async respond<T>(work: () => T, options?: RequestOptions, latency = this.options.latencyMs ?? 0): Promise<T> {
    await wait(latency, options?.signal);
    if (this.options.fail) {
      throw new CatalogError(503, "catalog_unavailable", "The catalog is temporarily unavailable.");
    }
    return work();
  }

  listMovies(query: MovieQuery, options?: RequestOptions): Promise<Page<MovieSummary>> {
    return this.respond(() => {
      // Round-trip through the wire format so the fixture client validates exactly like the API would.
      const params = toSearchParams(query);
      params.set("sort", query.sort);
      params.set("limit", String(query.limit));
      if (query.cursor) params.set("cursor", query.cursor);
      return this.engine.listMovies(parseMovieQuery(params));
    }, options);
  }

  getMovie(id: string, options?: RequestOptions): Promise<MovieDetail> {
    return this.respond(() => this.engine.getMovie(id), options, 0);
  }

  getCredits(id: string, options?: RequestOptions): Promise<MovieCredits> {
    return this.respond(() => this.engine.getCredits(id), options, 0);
  }

  listGenres(options?: RequestOptions): Promise<GenreRef[]> {
    return this.respond(() => this.engine.listGenres(), options, 0);
  }

  listCollections(options?: RequestOptions): Promise<Collection[]> {
    return this.respond(() => this.engine.listCollections(), options, 0);
  }

  getCollectionMovies(slug: string, options?: RequestOptions): Promise<Page<MovieSummary>> {
    return this.respond(() => this.engine.getCollectionMovies(slug), options, 0);
  }

  getDiscover(options?: RequestOptions): Promise<Discover> {
    return this.respond(
      () => ({
        blocks: this.engine.listCollections().map((c) => ({ ...c, items: this.engine.getCollectionMovies(c.slug).items })),
        catalog: { movie_count: this.engine.movieCount, catalog_version: this.engine.version },
      }),
      options,
      0,
    );
  }
}
