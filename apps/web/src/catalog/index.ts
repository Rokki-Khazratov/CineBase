import { FixtureEngine } from "./engine";
import { FixtureCatalog } from "./fixture-client";
import { loadFixtureData } from "./fixture-data";

export * from "./types";
export { buildMovieQuery, defaultSort, parseMovieQuery, queryKey, toSearchParams, MAX_QUERY_LENGTH } from "./query";

const engine = new FixtureEngine(loadFixtureData());

/** Shared fixture-backed catalog. Swap this export for an HTTP client when the API exists. */
export const catalog = new FixtureCatalog(engine);

export const catalogMeta = { movieCount: engine.movieCount, version: engine.version, ids: () => engine.allIds() };
