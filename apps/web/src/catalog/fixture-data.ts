/**
 * Loads the raw fixture files, validates them and merges later import batches.
 * Everything here runs once at module load; the result is plain data shared by server and client.
 */
import { z } from "zod";
import rawCollections from "@fixtures/collections.json";
import rawGenres from "@fixtures/genres.json";
import reimportStalker from "@fixtures/import-batches/0001-reimport-stalker.json";
import rawMovies from "@fixtures/movies.json";
import rawPeople from "@fixtures/people.json";

const isoDate = z.string().regex(/^\d{4}-\d{2}-\d{2}$/);
const slug = z.string().regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/);
const externalId = z.object({ provider: z.string().min(1), external_id: z.string().min(1) });
const alternateTitle = z.object({ title: z.string().min(1), locale: z.string().nullable() });

export const genreSchema = z.object({ slug, name: z.string().min(1) });
export const personSchema = z.object({ id: z.uuid(), slug, name: z.string().min(1) });
export const creditSchema = z.object({
  person: slug,
  department: z.string().min(1),
  job: z.string().min(1),
  character: z.string().min(1).nullable(),
  order: z.number().int().nonnegative(),
});
export const movieSchema = z
  .object({
    id: z.uuid(),
    slug,
    title: z.string().min(1),
    original_title: z.string().min(1).nullable(),
    original_language: z.string().min(2).nullable(),
    status: z.enum(["released", "announced"]),
    release_date: isoDate.nullable(),
    release_country: z.string().length(2).nullable(),
    release_year: z.number().int().min(1870).nullable(),
    runtime_minutes: z.number().int().positive().nullable(),
    genres: z.array(slug).min(1),
    synopsis: z.string().min(1).nullable(),
    alternate_titles: z.array(alternateTitle),
    external_ids: z.array(externalId).min(1),
    poster: z.object({ file: z.string().regex(/^posters\/[a-z0-9-]+\.svg$/), style: z.string() }).nullable(),
    credits: z.array(creditSchema),
  })
  .strict()
  .refine((m) => m.original_title !== m.title, { message: "original_title must be null when equal to title" })
  .refine((m) => !m.release_date || Number(m.release_date.slice(0, 4)) === m.release_year, {
    message: "release_date and release_year disagree",
  });
export const collectionSchema = z.object({
  slug,
  title: z.string().min(1),
  description: z.string().min(1),
  movies: z.array(slug).min(1),
});
export const importBatchSchema = z.object({
  description: z.string(),
  imported_at: z.string(),
  records: z.array(
    z.object({
      external_id: externalId,
      title: z.string().min(1),
      release_year: z.number().int().nullable().optional(),
      runtime_minutes: z.number().int().positive().nullable().optional(),
      synopsis: z.string().nullable().optional(),
      alternate_titles: z.array(alternateTitle).optional(),
    }),
  ),
});

export type RawMovie = z.infer<typeof movieSchema>;
export type RawPerson = z.infer<typeof personSchema>;
export type RawGenre = z.infer<typeof genreSchema>;
export type RawCollection = z.infer<typeof collectionSchema>;
export type ImportBatch = z.infer<typeof importBatchSchema>;

export type FixtureData = {
  movies: RawMovie[];
  people: RawPerson[];
  genres: RawGenre[];
  collections: RawCollection[];
};

export const CATALOG_VERSION = "fixtures-2026-10-26";

/**
 * Merges an import batch into the catalog. A record whose (provider, external_id) is already known
 * updates that film in place: its UUID never changes, non-null incoming values fill or replace fields,
 * and alternate titles are unioned. Unknown external IDs are rejected because fixture batches only
 * carry partial records.
 */
export function applyImportBatch(movies: RawMovie[], batch: ImportBatch): RawMovie[] {
  const byExternal = new Map<string, number>();
  movies.forEach((m, i) => m.external_ids.forEach((e) => byExternal.set(`${e.provider}:${e.external_id}`, i)));
  const next = movies.map((m) => ({ ...m, alternate_titles: [...m.alternate_titles] }));
  for (const record of batch.records) {
    const key = `${record.external_id.provider}:${record.external_id.external_id}`;
    const index = byExternal.get(key);
    if (index === undefined) throw new Error(`Import batch references unknown external ID ${key}`);
    const movie = next[index];
    if (record.release_year != null && movie.release_year == null) movie.release_year = record.release_year;
    if (record.runtime_minutes != null) movie.runtime_minutes = record.runtime_minutes;
    if (record.synopsis != null) movie.synopsis = record.synopsis;
    const seen = new Set([movie.title, movie.original_title, ...movie.alternate_titles.map((a) => a.title)]);
    for (const alt of record.alternate_titles ?? []) {
      if (!seen.has(alt.title)) {
        movie.alternate_titles.push(alt);
        seen.add(alt.title);
      }
    }
  }
  return next;
}

export function loadFixtureData(): FixtureData {
  const movies = z.array(movieSchema).parse(rawMovies);
  const batch = importBatchSchema.parse(reimportStalker);
  return {
    movies: applyImportBatch(movies, batch),
    people: z.array(personSchema).parse(rawPeople),
    genres: z.array(genreSchema).parse(rawGenres),
    collections: z.array(collectionSchema).parse(rawCollections),
  };
}

export const rawFixtures = { movies: rawMovies, people: rawPeople, genres: rawGenres, collections: rawCollections };
