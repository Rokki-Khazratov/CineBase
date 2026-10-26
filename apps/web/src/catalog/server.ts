import { cacheLife } from "next/cache";
import { catalog, CATALOG_SOURCE } from "./index";
import { buildMovieQuery } from "./query";
import { CatalogError, type CatalogInfo, type Discover, type GenreRef, type MovieCredits, type MovieDetail } from "./types";

/*
 * Cached reads for Server Components. The catalog changes only when an import runs, so pages can be served
 * from cache and refreshed in the background (Next.js `use cache`, see next.config.ts cacheComponents).
 */

export async function getGenres(): Promise<GenreRef[]> {
  "use cache";
  cacheLife("hours");
  return catalog.listGenres();
}

export async function getDiscover(): Promise<Discover> {
  "use cache";
  cacheLife("hours");
  return catalog.getDiscover();
}

export async function getCatalogInfo(): Promise<CatalogInfo> {
  "use cache";
  cacheLife("hours");
  return catalog.getCatalogInfo();
}

/**
 * Film IDs to prerender at build time: every fixture film, or the best-known page of the API catalog.
 * Other films render on first request and are cached after that.
 */
export async function getPrerenderIds(): Promise<string[]> {
  "use cache";
  cacheLife("hours");
  const page = await catalog.listMovies(buildMovieQuery({ sort: "notable", limit: 48 }));
  return page.items.map((m) => m.id);
}

/** The film, or null when the catalog has no film with this ID. Other errors are thrown. */
export async function getMovie(id: string): Promise<MovieDetail | null> {
  "use cache";
  cacheLife("hours");
  try {
    return await catalog.getMovie(id);
  } catch (err) {
    if (err instanceof CatalogError && (err.status === 404 || err.status === 422)) return null;
    throw err;
  }
}

export async function getCredits(id: string): Promise<MovieCredits> {
  "use cache";
  cacheLife("hours");
  return catalog.getCredits(id);
}

export { CATALOG_SOURCE };
