import { FixtureEngine } from "./engine";
import { FixtureCatalog } from "./fixture-client";
import { loadFixtureData } from "./fixture-data";

/** The bundled 43-film catalog. Loaded on demand so API builds do not ship the fixture data to browsers. */
export function createFixtureCatalog(): FixtureCatalog {
  return new FixtureCatalog(new FixtureEngine(loadFixtureData()));
}
