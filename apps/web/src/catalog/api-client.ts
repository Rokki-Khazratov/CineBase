import { toSearchParams } from "./query";
import {
  CatalogError,
  type ApiErrorBody,
  type CatalogClient,
  type CatalogInfo,
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

type Fetch = typeof fetch;

/**
 * CatalogClient for the CineBase API (`/api/v1`). In the browser `baseUrl` is empty and requests go to the
 * same origin, which Next.js rewrites to the API; on the server it is the API's own address.
 */
export class ApiCatalog implements CatalogClient {
  constructor(
    private readonly baseUrl: string,
    private readonly fetcher: Fetch = (...args) => fetch(...args),
  ) {}

  private async get<T>(path: string, options?: RequestOptions): Promise<T> {
    let response: Response;
    try {
      response = await this.fetcher(`${this.baseUrl}/api/v1${path}`, {
        signal: options?.signal,
        headers: { Accept: "application/json" },
      });
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") throw err;
      throw new CatalogError(503, "catalog_unavailable", "The catalog is temporarily unavailable.");
    }
    if (response.ok) return (await response.json()) as T;

    let body: ApiErrorBody | null = null;
    try {
      body = (await response.json()) as ApiErrorBody;
    } catch {
      body = null;
    }
    const error = body?.error;
    if (error?.code) {
      throw new CatalogError(response.status, error.code, error.message, error.fields, error.request_id);
    }
    const code = response.status >= 500 ? "catalog_unavailable" : "unexpected_error";
    throw new CatalogError(response.status, code, "The catalog is temporarily unavailable.");
  }

  listMovies(query: MovieQuery, options?: RequestOptions): Promise<Page<MovieSummary>> {
    const params = toSearchParams(query);
    params.set("sort", query.sort);
    params.set("limit", String(query.limit));
    if (query.cursor) params.set("cursor", query.cursor);
    return this.get(`/movies?${params}`, options);
  }

  getMovie(id: string, options?: RequestOptions): Promise<MovieDetail> {
    return this.get(`/movies/${encodeURIComponent(id)}`, options);
  }

  getCredits(id: string, options?: RequestOptions): Promise<MovieCredits> {
    return this.get(`/movies/${encodeURIComponent(id)}/credits`, options);
  }

  listGenres(options?: RequestOptions): Promise<GenreRef[]> {
    return this.get("/genres", options);
  }

  getCatalogInfo(options?: RequestOptions): Promise<CatalogInfo> {
    return this.get("/catalog", options);
  }

  listCollections(options?: RequestOptions): Promise<Collection[]> {
    return this.get("/collections", options);
  }

  getCollectionMovies(slug: string, options?: RequestOptions): Promise<Page<MovieSummary>> {
    return this.get(`/collections/${encodeURIComponent(slug)}/movies`, options);
  }

  getDiscover(options?: RequestOptions): Promise<Discover> {
    return this.get("/discover", options);
  }
}
