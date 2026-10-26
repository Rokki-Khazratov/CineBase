import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { z } from "zod";
import rawBatch from "@fixtures/import-batches/0001-reimport-stalker.json";
import {
  applyImportBatch,
  collectionSchema,
  genreSchema,
  importBatchSchema,
  loadFixtureData,
  movieSchema,
  personSchema,
  rawFixtures,
} from "./fixture-data";

const artDir = fileURLToPath(new URL("../../../../fixtures/art/", import.meta.url));

describe("fixture files", () => {
  it("match their schemas", () => {
    expect(() => z.array(movieSchema).parse(rawFixtures.movies)).not.toThrow();
    expect(() => z.array(personSchema).parse(rawFixtures.people)).not.toThrow();
    expect(() => z.array(genreSchema).parse(rawFixtures.genres)).not.toThrow();
    expect(() => z.array(collectionSchema).parse(rawFixtures.collections)).not.toThrow();
    expect(() => importBatchSchema.parse(rawBatch)).not.toThrow();
  });

  const data = loadFixtureData();
  const { movies, people, genres, collections } = data;

  it("has 30–50 films, 3+ collections and unique identifiers", () => {
    expect(movies.length).toBeGreaterThanOrEqual(30);
    expect(movies.length).toBeLessThanOrEqual(50);
    expect(collections.length).toBeGreaterThanOrEqual(3);
    for (const values of [
      movies.map((m) => m.id),
      movies.map((m) => m.slug),
      movies.flatMap((m) => m.external_ids.map((e) => `${e.provider}:${e.external_id}`)),
      people.map((p) => p.id),
      people.map((p) => p.slug),
      genres.map((g) => g.slug),
      collections.map((c) => c.slug),
    ]) {
      expect(new Set(values).size).toBe(values.length);
    }
  });

  it("only references people, genres, films and poster files that exist", () => {
    const personSlugs = new Set(people.map((p) => p.slug));
    const genreSlugs = new Set(genres.map((g) => g.slug));
    const movieSlugs = new Set(movies.map((m) => m.slug));
    for (const m of movies) {
      m.credits.forEach((c) => expect(personSlugs, `${m.slug} → ${c.person}`).toContain(c.person));
      m.genres.forEach((g) => expect(genreSlugs, `${m.slug} → ${g}`).toContain(g));
      if (m.poster) expect(existsSync(artDir + m.poster.file), m.poster.file).toBe(true);
      expect(m.credits.some((c) => c.job === "Director"), `${m.slug} has a director`).toBe(true);
    }
    collections.forEach((c) => c.movies.forEach((s) => expect(movieSlugs).toContain(s)));
  });

  it("covers the edge cases required by TECHNICAL_SPEC §9", () => {
    const titles = new Map<string, number>();
    movies.forEach((m) => titles.set(m.title, (titles.get(m.title) ?? 0) + 1));
    const sameTitle = [...titles.values()].filter((n) => n > 1);
    expect(sameTitle.length, "same title, different years").toBeGreaterThanOrEqual(3);
    expect(movies.some((m) => /^\d/.test(m.title)), "title starting with a number").toBe(true);
    expect(movies.filter((m) => m.alternate_titles.length > 0).length, "aliases").toBeGreaterThanOrEqual(10);
    expect(new Set(movies.map((m) => m.original_language)).size, "languages").toBeGreaterThanOrEqual(8);
    expect(movies.some((m) => /[̀-ͯ]/.test(m.title.normalize("NFD"))), "diacritics").toBe(true);
    expect(movies.some((m) => m.status === "announced"), "announced release").toBe(true);
    expect(movies.some((m) => m.release_date === null), "unknown date").toBe(true);
    expect(movies.some((m) => m.runtime_minutes === null), "unknown runtime").toBe(true);
    expect(movies.some((m) => m.poster === null), "missing poster").toBe(true);
    expect(movies.some((m) => m.title.length > 60), "long title").toBe(true);
    const multiRole = movies.some((m) => {
      const credits = m.credits.map((c) => c.person);
      return new Set(credits).size < credits.length;
    });
    expect(multiRole, "one person with several roles in a film").toBe(true);
    expect(movies.some((m) => m.credits.some((c) => c.character?.includes(" / "))), "one actor, several characters").toBe(true);
  });

  it("never stores unknown values as zero or empty strings", () => {
    for (const m of movies) {
      expect(m.runtime_minutes).not.toBe(0);
      expect(m.synopsis).not.toBe("");
      expect(m.release_year).not.toBe(0);
    }
  });
});

describe("import batches", () => {
  const base = z.array(movieSchema).parse(rawFixtures.movies);
  const batch = importBatchSchema.parse(rawBatch);

  it("merges a repeated external ID into the existing film and keeps its UUID", () => {
    const before = base.find((m) => m.slug === "stalker-1979")!;
    const merged = applyImportBatch(base, batch);
    const after = merged.find((m) => m.slug === "stalker-1979")!;
    expect(merged).toHaveLength(base.length);
    expect(after.id).toBe(before.id);
    expect(before.runtime_minutes).toBeNull();
    expect(after.runtime_minutes).toBe(162);
    expect(after.alternate_titles.map((a) => a.title)).toContain("Stalker (Сталкер)");
  });

  it("is idempotent", () => {
    const once = applyImportBatch(base, batch);
    expect(applyImportBatch(once, batch)).toEqual(once);
  });

  it("rejects records for unknown external IDs", () => {
    const unknown = { ...batch, records: [{ ...batch.records[0], external_id: { provider: "x", external_id: "y" } }] };
    expect(() => applyImportBatch(base, unknown)).toThrow(/unknown external ID/);
  });
});
