import { describe, expect, it } from "vitest";
import { FixtureEngine } from "./engine";
import { FixtureCatalog } from "./fixture-client";
import { loadFixtureData } from "./fixture-data";
import { buildMovieQuery, parseMovieQuery, toSearchParams } from "./query";
import { CatalogError, type MovieQuery, type MovieSummary } from "./types";

const engine = new FixtureEngine(loadFixtureData());
const catalog = new FixtureCatalog(engine);

const list = (partial: Partial<MovieQuery>) => catalog.listMovies(buildMovieQuery(partial));
const label = (m: MovieSummary) => `${m.title} (${m.year ?? "?"})`;

async function listAll(partial: Partial<MovieQuery>): Promise<MovieSummary[]> {
  const out: MovieSummary[] = [];
  let cursor: string | null = null;
  do {
    const page = await list({ ...partial, cursor });
    out.push(...page.items);
    cursor = page.next_cursor;
  } while (cursor);
  return out;
}

async function catalogError(promise: Promise<unknown>): Promise<CatalogError> {
  try {
    await promise;
  } catch (error) {
    if (error instanceof CatalogError) return error;
    throw error;
  }
  throw new Error("expected a CatalogError");
}

describe("search relevance", () => {
  it("returns both films that share a title, told apart by year and director", async () => {
    const { items } = await list({ q: "suspiria" });
    expect(items.slice(0, 2).map(label).sort()).toEqual(["Suspiria (1977)", "Suspiria (2018)"]);
    const directors = items.slice(0, 2).map((m) => m.directors.map((d) => d.name).join());
    expect(directors.sort()).toEqual(["Dario Argento", "Luca Guadagnino"]);
  });

  it("puts the requested year first for 'Title (YYYY)' and still shows the other version", async () => {
    const { items } = await list({ q: "Suspiria (1977)" });
    expect(items.map(label)).toEqual(["Suspiria (1977)", "Suspiria (2018)"]);
    const thing = await list({ q: "The Thing (2011)" });
    expect(label(thing.items[0])).toBe("The Thing (2011)");
  });

  it("ranks exact matches before prefix, word-prefix and substring matches", async () => {
    const { items } = await list({ q: "dune" });
    expect(items.map(label)).toEqual([
      "Dune (2021)",
      "Dune (1984)",
      "Dune: Part Two (2024)",
      "Dune: Part Three (2026)",
    ]);
  });

  it("ignores case, accents and punctuation", async () => {
    expect(label((await list({ q: "AMELIE" })).items[0])).toBe("Amélie (2001)");
    expect(label((await list({ q: "oceans 11" })).items[0])).toBe("Ocean's 11 (1960)");
    expect(label((await list({ q: "paris texas" })).items[0])).toBe("Paris, Texas (1984)");
  });

  it("finds films by original and romanized alternate titles, each film once", async () => {
    expect(label((await list({ q: "Солярис" })).items[0])).toBe("Solaris (1972)");
    expect(label((await list({ q: "shichinin no samurai" })).items[0])).toBe("Seven Samurai (1954)");
    expect(label((await list({ q: "Tokyo monogatari" })).items[0])).toBe("Tokyo Story (1953)");
    expect(label((await list({ q: "無間道" })).items[0])).toBe("Infernal Affairs (2002)");
    // "Ocean's Eleven" is the 2001 title and an alias of the 1960 film; each appears once.
    const oceans = (await list({ q: "ocean's eleven" })).items.map(label);
    expect(oceans).toEqual(["Ocean's Eleven (2001)", "Ocean's 11 (1960)"]);
  });

  it("matches 8½ by its spelled-out forms", async () => {
    expect(label((await list({ q: "8 1/2" })).items[0])).toBe("8½ (1963)");
    expect(label((await list({ q: "8½" })).items[0])).toBe("8½ (1963)");
    expect(label((await list({ q: "otto e mezzo" })).items[0])).toBe("8½ (1963)");
  });

  it("matches a long title by any of its words and by its short alias", async () => {
    const long = "Dr. Strangelove or: How I Learned to Stop Worrying and Love the Bomb (1964)";
    expect(label((await list({ q: "stop worrying" })).items[0])).toBe(long);
    expect(label((await list({ q: "dr strangelove" })).items[0])).toBe(long);
  });

  it("falls back to similarity for longer misspelled queries only", async () => {
    expect(label((await list({ q: "stalkr" })).items[0])).toBe("Stalker (1979)");
    expect(label((await list({ q: "labyrinht" })).items[0])).toBe("Pan's Labyrinth (2006)");
    expect((await list({ q: "stalkr" })).items.length).toBeLessThan(4);
    // Short queries never use fuzzy matching.
    expect((await list({ q: "zq" })).items).toEqual([]);
  });

  it("keeps numbers in titles searchable", async () => {
    expect(label((await list({ q: "2001" })).items[0])).toBe("2001: A Space Odyssey (1968)");
    expect(label((await list({ q: "12 angry" })).items[0])).toBe("12 Angry Men (1957)");
  });

  it("returns an empty page for punctuation-only queries", async () => {
    expect(await list({ q: "?!" })).toEqual({ items: [], next_cursor: null, has_more: false, total: 0 });
  });
});

describe("filters", () => {
  it("combines genres with OR", async () => {
    const items = await listAll({ genres: ["western", "animation"], sort: "title_asc" });
    expect(items.map((m) => m.title)).toEqual([
      "Spirited Away",
      "The Magnificent Seven",
      "True Grit",
      "True Grit",
    ]);
  });

  it("combines filter groups with AND, with inclusive year bounds", async () => {
    const items = await listAll({ genres: ["horror"], year_from: 1977, year_to: 1982, sort: "release_desc" });
    expect(items.map(label)).toEqual(["The Thing (1982)", "Nosferatu the Vampyre (1979)", "Suspiria (1977)"]);
  });

  it("excludes films with unknown runtime from a runtime filter", async () => {
    const items = await listAll({ runtime_max: 400 });
    const ids = items.map((m) => m.title);
    expect(ids).not.toContain("Dune: Part Three");
    expect(items.every((m) => m.runtime_minutes !== null && m.runtime_minutes <= 400)).toBe(true);
    expect(items).toHaveLength(engine.movieCount - 1);
  });

  it("applies filters to search results", async () => {
    const { items } = await list({ q: "nosferatu", year_from: 2000 });
    expect(items.map(label)).toEqual(["Nosferatu (2024)"]);
  });
});

describe("sorting", () => {
  it("title_asc orders by normalized title, then year", async () => {
    const titles = (await listAll({ sort: "title_asc" })).map(label);
    expect(titles.slice(0, 3)).toEqual(["12 Angry Men (1957)", "2001: A Space Odyssey (1968)", "8½ (1963)"]);
    expect(titles.indexOf("Suspiria (1977)")).toBe(titles.indexOf("Suspiria (2018)") - 1);
  });

  it("release_desc starts with the announced film and puts year-only dates after full dates of that year", async () => {
    const items = await listAll({ sort: "release_desc" });
    expect(label(items[0])).toBe("Dune: Part Three (2026)");
    const in1984 = items.filter((m) => m.year === 1984).map((m) => m.title);
    expect(in1984).toEqual(["Dune", "Paris, Texas"]);
  });

  it("release_asc and runtime_desc mirror their counterparts, unknown values still last", async () => {
    const oldest = await listAll({ sort: "release_asc" });
    expect(label(oldest[0])).toBe("Nosferatu (1922)");
    const longest = await listAll({ sort: "runtime_desc" });
    expect(longest.at(-1)?.title).toBe("Dune: Part Three");
    const runtimes = longest.slice(0, -1).map((m) => m.runtime_minutes as number);
    expect(runtimes).toEqual([...runtimes].sort((a, b) => b - a));
  });

  it("browsing defaults to best known, which ties on fixtures and falls back to newest year", async () => {
    const items = await listAll({});
    expect(items.map((m) => m.year ?? 0)).toEqual(items.map((m) => m.year ?? 0).sort((a, b) => b - a));
  });

  it("hides announced films on request and reports the total on the first page only", async () => {
    const all = await list({ limit: 5 });
    expect(all.total).toBe(engine.movieCount);
    const released = await list({ exclude: ["unreleased"], limit: 5 });
    expect(released.total).toBe(engine.movieCount - 1);
    expect((await list({ exclude: ["unreleased"], limit: 5, cursor: released.next_cursor })).total).toBeNull();
  });

  it("runtime_asc puts unknown runtimes last", async () => {
    const items = await listAll({ sort: "runtime_asc" });
    expect(items.at(-1)?.title).toBe("Dune: Part Three");
    const runtimes = items.slice(0, -1).map((m) => m.runtime_minutes as number);
    expect(runtimes).toEqual([...runtimes].sort((a, b) => a - b));
  });
});

describe("pagination", () => {
  it("walks the whole catalog without duplicates or gaps", async () => {
    for (const sort of ["notable", "title_asc", "release_desc", "release_asc", "runtime_asc", "runtime_desc"] as const) {
      const pages: number[] = [];
      const seen: string[] = [];
      let cursor: string | null = null;
      do {
        const page = await list({ sort, limit: 10, cursor });
        pages.push(page.items.length);
        seen.push(...page.items.map((m) => m.id));
        expect(page.has_more).toBe(page.next_cursor !== null);
        cursor = page.next_cursor;
      } while (cursor);
      expect(new Set(seen).size).toBe(engine.movieCount);
      expect(pages).toEqual([10, 10, 10, 10, 3]);
    }
  });

  it("rejects a cursor used with different filters (400)", async () => {
    const first = await list({ sort: "title_asc", limit: 5 });
    const error = await catalogError(list({ sort: "release_desc", limit: 5, cursor: first.next_cursor }));
    expect(error.status).toBe(400);
    expect(error.code).toBe("invalid_cursor");
  });

  it("rejects a malformed cursor (400)", async () => {
    expect((await catalogError(list({ cursor: "not-a-cursor" }))).status).toBe(400);
    expect((await catalogError(list({ cursor: "eyJ2IjoxfQ" }))).status).toBe(400);
  });
});

describe("parameter validation", () => {
  it.each([
    [{ q: "x".repeat(201) }, "q"],
    [{ year_from: "2000", year_to: "1990" }, "year_to"],
    [{ year_from: "nineteen" }, "year_from"],
    [{ runtime_max: "0" }, "runtime_max"],
    [{ sort: "rating" }, "sort"],
    [{ sort: "relevance" }, "sort"],
    [{ limit: "49" }, "limit"],
    [{ limit: "0" }, "limit"],
    [{ exclude: "musicals" }, "exclude"],
  ])("rejects %j with 422 on %s", (params, field) => {
    try {
      parseMovieQuery(params);
      throw new Error("expected 422");
    } catch (error) {
      expect(error).toBeInstanceOf(CatalogError);
      expect((error as CatalogError).status).toBe(422);
      expect((error as CatalogError).fields).toHaveProperty(field);
    }
  });

  it("accepts 200 characters, trims q and defaults the sort", () => {
    expect(parseMovieQuery({ q: "x".repeat(200) }).q).toHaveLength(200);
    expect(parseMovieQuery({ q: "  dune " })).toMatchObject({ q: "dune", sort: "relevance", limit: 24 });
    expect(parseMovieQuery({})).toMatchObject({ q: "", sort: "notable", exclude: [] });
  });

  it("builds canonical URLs without defaults", () => {
    const query = parseMovieQuery(new URLSearchParams("q=dune&genre=war&genre=drama&sort=relevance&year_from=1980"));
    expect(toSearchParams(query).toString()).toBe("q=dune&genre=drama&genre=war&year_from=1980");
    expect(toSearchParams(buildMovieQuery({ sort: "title_asc" })).toString()).toBe("sort=title_asc");
    const hidden = parseMovieQuery(new URLSearchParams("exclude=tv,short&exclude=short"));
    expect(hidden.exclude).toEqual(["short", "tv"]);
    expect(toSearchParams(hidden).toString()).toBe("exclude=short&exclude=tv");
  });

  it("validates queries passed to the client the same way", async () => {
    const error = await catalogError(list({ q: "", sort: "relevance" }));
    expect(error.status).toBe(422);
    expect(error.toJSON().error).toMatchObject({ code: "invalid_parameters", fields: { sort: expect.any(String) } });
    expect(error.toJSON().error.request_id).toMatch(/^req_/);
  });
});

describe("details, credits and errors", () => {
  it("returns details with release, alternate titles and provenance", async () => {
    const [stalker] = (await list({ q: "stalker" })).items;
    const detail = await catalog.getMovie(stalker.id);
    expect(detail.original_title).toBe("Сталкер");
    expect(detail.release).toEqual({ status: "released", date: null, country: "SU" });
    expect(detail.provenance.sources).toEqual([{ name: "cinebase-fixture", external_id: "cbf-0035" }]);
    expect(detail.backdrop).toBeNull();
  });

  it("lists a person with several roles in one film once per role", async () => {
    const [suspiria2018] = (await list({ q: "Suspiria (2018)" })).items;
    const credits = await catalog.getCredits(suspiria2018.id);
    const swinton = credits.cast.find((c) => c.person.name === "Tilda Swinton");
    expect(swinton?.character).toContain("Mother Markos");
    const [solaris] = (await list({ q: "Solaris (2002)" })).items;
    const crew = (await catalog.getCredits(solaris.id)).crew.filter((c) => c.person.name === "Steven Soderbergh");
    expect(crew.map((c) => c.job)).toEqual(["Director", "Screenplay", "Director of Photography", "Editor"]);
  });

  it("returns 404 for an unknown film", async () => {
    const error = await catalogError(catalog.getMovie("00000000-0000-4000-8000-000000000000"));
    expect(error.status).toBe(404);
    expect((await catalogError(catalog.getMovie("not-a-uuid"))).status).toBe(404);
  });

  it("can simulate an outage and honours abort signals", async () => {
    const failing = catalog.withOptions({ fail: true });
    expect((await catalogError(failing.listMovies(buildMovieQuery()))).status).toBe(503);
    const slow = catalog.withOptions({ latencyMs: 1000 });
    const controller = new AbortController();
    const pending = slow.listMovies(buildMovieQuery(), { signal: controller.signal });
    controller.abort();
    await expect(pending).rejects.toMatchObject({ name: "AbortError" });
  });

  it("builds discover blocks from collections", async () => {
    const discover = await catalog.getDiscover();
    expect(discover.blocks.map((b) => b.slug)).toEqual(["told-twice", "beyond-english", "under-100-minutes"]);
    expect(discover.catalog.movie_count).toBe(43);
    const short = discover.blocks[2].items;
    expect(short.every((m) => m.runtime_minutes !== null && m.runtime_minutes < 100)).toBe(true);
  });
});
