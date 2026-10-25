# CineBase fixtures

Hand-authored catalog data for the Phase 1 web prototype. The web app reads these files directly through
`FixtureCatalog` (`apps/web/src/catalog`); there is no database or backend yet.

| File | Contents |
| --- | --- |
| `movies.json` | 43 films: stable UUID, titles, original title/language, release, runtime, genres, original synopsis, alternate titles, external IDs, poster reference and credits |
| `people.json` | Everyone referenced by credits (`slug` is the join key used in `movies.json`) |
| `genres.json` | Genre slugs and display names |
| `collections.json` | Editorial rows shown on Home |
| `import-batches/` | Later imports. Records are merged into an existing film by `(provider, external_id)`; the film keeps its UUID |
| `art/posters/` | Generated SVG posters (`node scripts/generate-posters.mjs`). Synthetic placeholders, not studio artwork |

Rules the data follows (and the tests enforce, see `apps/web/src/catalog/fixtures.test.ts`):

- Unknown values are `null`, never `0` or an empty string (for example `release_date` for films whose exact
  premiere date was not verified, or `runtime_minutes` for an announced film).
- `original_title` is `null` when it is the same as `title`.
- Synopses are original one- or two-sentence descriptions written for CineBase, without spoilers.
- Facts (titles, years, directors, cast) describe real films; posters are deliberately not real artwork.
- Some films have `poster: null` on purpose so the UI's missing-poster state is always exercised.

After editing `movies.json`, regenerate posters and run the fixture tests:

```sh
node scripts/generate-posters.mjs
pnpm fixtures:validate
```
