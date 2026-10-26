# CineBase

A film catalog built around fast search, useful movie pages and a carefully designed browsing experience. CineBase is the first standalone project in the Cinephily plan; its catalog API will later support the first mobile app.

**Status:** Phase 1 web prototype. Home, search with filters and sorting, and film pages run on 43 hand-made fixture films in a Next.js app. There is no backend, database or user accounts yet; the replacement API is planned for Phase 2.

- [Technical specification and phased tasks (RU)](docs/TECHNICAL_SPEC.md)
- [UI and UX design direction (RU)](docs/UI_DESIGN_DIRECTION.md)
- [Legacy audit and restart decision (RU)](docs/LEGACY_AUDIT.md)
- [Phase 1 verification record](docs/verification/phase-1.md)
- [Fixture data](fixtures/README.md)

## Run locally

Requirements: Node.js 24 LTS and pnpm 11 (`corepack enable` installs the pinned pnpm version).

```sh
pnpm install
pnpm dev                 # http://localhost:3000
```

| Command | What it does |
| --- | --- |
| `pnpm dev` | Development server with hot reload |
| `pnpm build` then `pnpm start` | Production build and server (port 3000; add `--port 3100` to change it) |
| `pnpm lint` / `pnpm typecheck` | ESLint and TypeScript checks |
| `pnpm test` | Unit tests (Vitest): catalog search, filters, paging, fixture rules |
| `pnpm test:e2e` | Browser tests (Playwright) in Chromium and WebKit, desktop and 360 px |
| `pnpm fixtures:validate` | Validates the fixture files only |
| `pnpm posters` | Regenerates the SVG posters from fixture data (`posters:check` verifies them) |

Before the first `pnpm test:e2e`, install the browsers once with `pnpm --filter web exec playwright install chromium webkit`. The e2e run builds the app and serves it on port 3100. If something is already listening on 3100 it is reused, so stop any older server first to test the current code.

Development switches for the results page, useful for checking states: add `_latency=2000` to the URL to slow responses, `_fail=1` to make every request fail, or `_fail=once` to fail until you press *Try again*.

## Product scope

Public browsing, title search, filters, film pages, credits, curated collections and responsive web UX. The separate Cinephily Base project owns user accounts, comments, chats and other social features.

## Implementation

- Web (built): Next.js 16 App Router, React 19, TypeScript, CSS Modules. All data access goes through one `CatalogClient` interface (`apps/web/src/catalog`), currently backed by bundled fixtures; it mirrors the planned API so the client can be swapped later.
- API (planned): Python, FastAPI, Pydantic, SQLAlchemy and Alembic.
- Database (planned): PostgreSQL.
- Data: deterministic fixtures in `fixtures/` plus, later, a replaceable external catalog adapter. Posters are generated SVG placeholders, not studio artwork.

The technical specification is the source of truth for phase scope and acceptance criteria.

## Repository history

This project continues the existing `Rokki-Khazratov/CineBase` repository. The earlier backend experiment remains available in Git history at commit `1f3163141e14a8d0b4b980e23c9a32b5343271ff`. Its obsolete scaffold is removed in the restart revision; its capabilities are assessed in the audit.

The MIT license covers this repository's code. Third-party catalog data and artwork retain their own terms.
