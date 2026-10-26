# CineBase

A film catalog built around fast search, useful movie pages and a carefully designed browsing experience. CineBase is the first standalone project in the Cinephily plan; its catalog API will later support the first mobile app.

**Status:**

- **Web app (Next.js):** Home, a Letterboxd-style Films page (browse by decade, genre, length, what to hide, and sort), search, and film pages with credits. It can run on the 43 bundled fixture films, or on the CineBase API.
- **API (FastAPI + PostgreSQL):** search, browse, film details, credits, people, genres, collections and discover.
- **Catalog:** imported from Wikidata, about 430,000 films (CC0). Posters come from Wikimedia Commons, where a freely licensed file exists. See [Catalog data sources](docs/DATA_SOURCES.md) for why Wikidata, and why the catalog contains no Letterboxd or TMDB data.
- There are no user accounts; those belong to Cinephily Base.

Docs:

- [Technical specification and phased tasks (RU)](docs/TECHNICAL_SPEC.md)
- [Catalog data sources and import plan (CB-301)](docs/DATA_SOURCES.md)
- [UI and UX design direction (RU)](docs/UI_DESIGN_DIRECTION.md)
- [Legacy audit and restart decision (RU)](docs/LEGACY_AUDIT.md)
- [Phase 1 verification record](docs/verification/phase-1.md)
- [Fixture data](fixtures/README.md)

## Run locally

Requirements:

- Node.js 24 LTS and pnpm 11 (`corepack enable` installs the pinned pnpm).
- For the API: Python 3.13, [uv](https://docs.astral.sh/uv/), and PostgreSQL 14 or newer with the `pg_trgm` extension (it ships with PostgreSQL).

### Web on fixtures (no database)

```sh
pnpm install
pnpm dev                 # http://localhost:3000
```

### Web on the full catalog

1. Start PostgreSQL. Either use a local server and create the databases (`createdb cinebase`, plus `createdb cinebase_test` for the API tests), or run `docker compose up -d db` and put the database URL from `apps/api/.env.example` into `apps/api/.env`.
2. Install the API, create the schema and load data (from `apps/api`):

   ```sh
   uv sync
   .venv/bin/cinebase migrate
   .venv/bin/cinebase seed-fixtures              # optional: the 43 fixture films, in seconds
   .venv/bin/cinebase import wikidata            # full catalog: ~430k films, about 70–80 min, ~2 GB
   .venv/bin/cinebase import wikidata --resume   # only if the import stopped
   .venv/bin/cinebase link-collections           # home page rows; run after an import
   .venv/bin/uvicorn cinebase_api.main:app --port 8000
   ```

   For a quick trial, use `import wikidata --limit 2000` instead of the full import. API docs: http://127.0.0.1:8000/docs.
3. Run the web app against it (from the repository root):

   ```sh
   NEXT_PUBLIC_CATALOG_SOURCE=api CINEBASE_API_URL=http://127.0.0.1:8000 pnpm dev
   ```

   You can also put both variables in `apps/web/.env.local` (see `apps/web/.env.example`). They are read at build time, so rebuild after changing them.

### Commands

| Command | What it does |
| --- | --- |
| `pnpm dev` | Web development server with hot reload |
| `pnpm build` then `pnpm start` | Production build and server (port 3000; add `--port 3100` to change it). In API mode the build needs the API running, because it prerenders the best-known films |
| `pnpm lint` / `pnpm typecheck` | ESLint and TypeScript checks |
| `pnpm test` | Web unit tests (Vitest) |
| `pnpm test:e2e` | Browser tests (Playwright) in Chromium and WebKit, desktop and 360 px |
| `pnpm fixtures:validate` | Validates the fixture files only |
| `pnpm posters` | Regenerates the fixture SVG posters (`posters:check` verifies them) |
| `.venv/bin/pytest` (in `apps/api`) | API and import tests on a real PostgreSQL (`CINEBASE_TEST_DATABASE_URL`, default `cinebase_test`). No network |
| `.venv/bin/ruff check .` / `.venv/bin/mypy` (in `apps/api`) | Lint and strict type checks |

**Browser tests.**

- Install the browsers once before the first run: `pnpm --filter web exec playwright install chromium webkit`.
- The run builds the app and serves it on port 3100. If something is already listening on 3100, that server is reused, so stop any older server first to test the current code.
- The tests expect the 43-film fixture catalog. To run them in API mode, start an API on a database that holds only the fixtures (`migrate`, `seed-fixtures`, `link-collections`), then run `NEXT_PUBLIC_CATALOG_SOURCE=api CINEBASE_API_URL=http://127.0.0.1:<port> pnpm test:e2e`.

**Development switches** for the Films page, useful for checking states:

- `_latency=2000` in the URL slows responses.
- `_fail=1` makes every request fail.
- `_fail=once` fails until you press *Try again*.

## Product scope

CineBase covers:

- public browsing, title search and filters;
- film pages and credits;
- curated collections;
- responsive web UX.

The separate Cinephily Base project owns user accounts, comments, chats and other social features.

## Implementation

**Web:**

- Next.js 16 App Router, React 19, TypeScript, CSS Modules.
- All data access goes through one `CatalogClient` interface (`apps/web/src/catalog`), backed by either the bundled fixtures or the HTTP API.
- The browser calls `/api/v1` on the web origin, which Next.js proxies to `CINEBASE_API_URL`.

**API:**

- Python 3.13, FastAPI, Pydantic, SQLAlchemy 2 and Alembic on PostgreSQL.
- Search uses normalized titles and `pg_trgm`, covering exact, prefix and substring matches and typos in every alternate title.
- Paging uses cursors; errors are typed and carry request IDs.

**Data:**

- **Import:** a resumable command-line import from the Wikidata Query Service, polite to the service: one request at a time, with backoff and `Retry-After`. It needs no API key.
- **Posters:** linked from Wikimedia Commons, with the licence and author shown on each film page.
- **Fixtures:** the bundled fixtures still work offline.

The technical specification is the source of truth for phase scope and acceptance criteria.

## Repository history

This project continues the existing `Rokki-Khazratov/CineBase` repository. The earlier backend experiment remains available in Git history at commit `1f3163141e14a8d0b4b980e23c9a32b5343271ff`. The restart revision removed its obsolete scaffold, and the audit assesses what it could do.

The MIT license covers this repository's code. Catalog data and artwork keep their own terms. Wikidata facts are CC0. Commons posters are under the licence shown with each one.
