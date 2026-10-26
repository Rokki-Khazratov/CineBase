import { ApiCatalog } from "./api-client";
import type { CatalogClient, MovieQuery, RequestOptions } from "./types";

export * from "./types";
export { buildMovieQuery, defaultSort, parseMovieQuery, queryKey, toSearchParams, MAX_QUERY_LENGTH, DEFAULT_LIMIT } from "./query";

/**
 * Where catalog data comes from, fixed at build time: `fixtures` (the bundled 43-film prototype catalog, the
 * default) or `api` (the CineBase API, see apps/api). Set with NEXT_PUBLIC_CATALOG_SOURCE.
 */
export const CATALOG_SOURCE: "api" | "fixtures" = process.env.NEXT_PUBLIC_CATALOG_SOURCE === "api" ? "api" : "fixtures";

/** Development knobs the results page uses to show loading and error states. */
export type CatalogOptions = { latencyMs?: number; fail?: boolean };

export interface Catalog extends CatalogClient {
  withOptions(options: CatalogOptions): Catalog;
}

function apiBaseUrl(): string {
  // Browsers call the same origin (rewritten to the API by next.config.ts); the server calls the API directly.
  if (typeof window !== "undefined") return "";
  return (process.env.CINEBASE_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");
}

function wait(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) return reject(new DOMException("The request was aborted.", "AbortError"));
    const timer = setTimeout(resolve, ms);
    signal?.addEventListener(
      "abort",
      () => {
        clearTimeout(timer);
        reject(new DOMException("The request was aborted.", "AbortError"));
      },
      { once: true },
    );
  });
}

/** The API client plus the same development knobs as the fixture client (`_latency`, `_fail`). */
class LiveCatalog extends ApiCatalog implements Catalog {
  constructor(private readonly options: CatalogOptions = {}) {
    super(apiBaseUrl(), async (input, init) => {
      if (options.latencyMs) await wait(options.latencyMs, init?.signal ?? undefined);
      if (options.fail) {
        const error = { code: "catalog_unavailable", message: "The catalog is temporarily unavailable.", request_id: "req_dev_fail" };
        return new Response(JSON.stringify({ error }), { status: 503 });
      }
      return fetch(input, init);
    });
  }

  withOptions(options: CatalogOptions): Catalog {
    return new LiveCatalog({ ...this.options, ...options });
  }
}

/** The fixture catalog, imported on first use so that it is a separate chunk an API build never loads. */
class LazyFixtureCatalog implements Catalog {
  private static loaded: Promise<Catalog> | null = null;

  constructor(private readonly options: CatalogOptions = {}) {}

  private client(): Promise<Catalog> {
    LazyFixtureCatalog.loaded ??= import("./fixture-catalog").then((m) => m.createFixtureCatalog());
    return LazyFixtureCatalog.loaded.then((c) => (Object.keys(this.options).length ? c.withOptions(this.options) : c));
  }

  withOptions(options: CatalogOptions): Catalog {
    return new LazyFixtureCatalog({ ...this.options, ...options });
  }

  listMovies(query: MovieQuery, options?: RequestOptions) {
    return this.client().then((c) => c.listMovies(query, options));
  }
  getMovie(id: string, options?: RequestOptions) {
    return this.client().then((c) => c.getMovie(id, options));
  }
  getCredits(id: string, options?: RequestOptions) {
    return this.client().then((c) => c.getCredits(id, options));
  }
  listGenres(options?: RequestOptions) {
    return this.client().then((c) => c.listGenres(options));
  }
  getCatalogInfo(options?: RequestOptions) {
    return this.client().then((c) => c.getCatalogInfo(options));
  }
  listCollections(options?: RequestOptions) {
    return this.client().then((c) => c.listCollections(options));
  }
  getCollectionMovies(slug: string, options?: RequestOptions) {
    return this.client().then((c) => c.getCollectionMovies(slug, options));
  }
  getDiscover(options?: RequestOptions) {
    return this.client().then((c) => c.getDiscover(options));
  }
}

function createCatalog(): Catalog {
  return CATALOG_SOURCE === "api" ? new LiveCatalog() : new LazyFixtureCatalog();
}

/** The only catalog screens use. */
export const catalog: Catalog = createCatalog();

/** Fixture responses are instant, so the results page adds a small delay to behave like a network round trip. */
export const SIMULATED_LATENCY = CATALOG_SOURCE === "fixtures";

export type { RequestOptions };
