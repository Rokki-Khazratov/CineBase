# CineBase

A film catalog built around fast search, useful movie pages and a carefully designed browsing experience. CineBase is the first standalone project in the Cinephily plan; its catalog API will later support the first mobile app.

**Status:** specification and clean restart. The web app and replacement API are planned; they are not implemented in this revision.

- [Technical specification and phased tasks (RU)](docs/TECHNICAL_SPEC.md)
- [Legacy audit and restart decision (RU)](docs/LEGACY_AUDIT.md)

## Product scope

Public browsing, title search, filters, film pages, credits, curated collections and responsive web UX. The separate Cinephily Base project owns user accounts, comments, chats and other social features.

## Planned implementation

- Web: React, TypeScript and Next.js App Router.
- API: Python, FastAPI, Pydantic, SQLAlchemy and Alembic.
- Database: PostgreSQL.
- Data: deterministic fixtures for development plus a replaceable external catalog adapter.

Exact supported versions, lockfiles and runnable commands are added during the foundation phase. The technical specification is the source of truth for phase scope and acceptance criteria.

## Repository history

This project continues the existing `Rokki-Khazratov/CineBase` repository. The earlier backend experiment remains available in Git history at commit `1f3163141e14a8d0b4b980e23c9a32b5343271ff`. Its obsolete scaffold is removed in the restart revision; its capabilities are assessed in the audit.

The MIT license covers this repository's code. Third-party catalog data and artwork retain their own terms.
