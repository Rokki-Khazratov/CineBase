# Catalog data sources (CB-301)

Decision record for where CineBase gets its film catalog, what it may store and show, and how the import runs. Terms were checked in October 2026; re-check them before any commercial launch.

## Decision

1. **Wikidata is the base catalog.** Its data is CC0, it needs no key, and it lists about 430,000 films. The import (`cinebase import wikidata`) builds the full catalog in our own PostgreSQL. The web app reads only from our API.
2. **Posters come only from Wikimedia Commons.** We use the file Wikidata links as the film's poster (P3383), and only if Commons reports a licence for it. Each film page shows the source, licence and author, and links to the Commons file page.
3. **No Letterboxd scraping, and no Letterboxd data in the catalog.** Letterboxd's page layout was a design reference only. Its terms forbid exporting content and building an index of it without written permission. API access is granted on request, and Letterboxd states it does not grant it for recommendation or personal projects.
4. **TMDB is optional enrichment, not the base.** Its free API is for non-commercial use with attribution; commercial use needs a written licence. If CineBase stays non-commercial, or gets that licence, a TMDB adapter could add plot synopses and better poster coverage. That would be an extra provider behind the same interface; the key stays on the backend.
5. **IMDb and OMDb are not used.** IMDb's datasets are for personal and non-commercial use and may not be republished as a film database. OMDb is a third-party wrapper with non-commercial terms. Wikidata already stores the IMDb ID and TMDB ID (P345, P4947), so links to those sites work without using their data.

## Comparison

| Source | Licence and access | Coverage for us | Use in CineBase |
| --- | --- | --- | --- |
| Wikidata | CC0. Free SPARQL endpoint; a descriptive User-Agent is required; 60 s per query | ~430k films; titles in many languages, dates, runtime, genres, cast and crew, IDs. No plot text, only one-line descriptions | **Base catalog** |
| Wikimedia Commons | Free licences only (public domain, CC BY, CC BY-SA); licence and author vary per file | Few posters: mostly pre-1930 and public-domain films | **Posters**, with per-file attribution |
| TMDB | Free for non-commercial use with attribution; commercial use needs a licence | Very wide: synopses, posters, backdrops, ratings | Possible later adapter, depending on terms |
| Letterboxd | Terms forbid exporting and indexing content; API on request, with excluded use cases | — | **Not used** |
| IMDb datasets | Personal and non-commercial only; no republishing as a database | Wide, but no posters or plots | Not used; IMDb ID kept for links |
| OMDb | Third-party API; non-commercial terms (not re-verified) | Derived from IMDb | Not used |

## What the import stores

From Wikidata, per film:

- canonical title (English label, else the original title or another label);
- original title (P1476) and language (P364);
- every label as an alternate title for search;
- earliest release date, with day precision only when Wikidata has it (a year stays a year);
- country of origin;
- runtime (P2047, converted to minutes);
- genres mapped to 18 slugs;
- directors, writers, composers, cinematographers and up to 30 cast;
- IMDb ID, TMDB ID and English Wikipedia link;
- the English description;
- the number of sitelinks, used as a "best known" score.

Each film is also classified by kind (feature, short, TV film; documentaries through their genre) and release status (released, announced, unknown). Adult-only items are skipped.

Coverage measured on the first 51,642 imported films:

| Field | Share of films |
| --- | --- |
| Release year | 99.7% |
| Exact release day | 31.7% |
| Runtime | 82.4% |
| At least one genre | 84% |
| Director | 98% |
| Poster with licence | 2.6% (1,268 public domain; the rest CC BY or CC BY-SA) |
| Plot synopsis | 0% (Wikidata has none) |

Missing values stay `null`; the UI says "Unknown" or shows a placeholder poster instead of inventing data.

## Attribution and media policy

- The footer credits Wikidata (CC0) for film facts and Wikimedia Commons for posters.
- Every Commons poster shows the source, licence and author next to it, linked to the file page, as CC BY and CC BY-SA require.
- Poster images are served from Commons' 500 px thumbnails, not copied to our storage. To mirror them later, keep the licence and author fields.
- Fixture posters are generated SVGs and are labelled "Illustrative".

## Limits and politeness

- One SPARQL request at a time, with a contact URL in the User-Agent (`CINEBASE_WIKIDATA_USER_AGENT`).
- Bounded retries with backoff; HTTP 429 `Retry-After` is honoured (capped at 5 min).
- Items are fetched in batches of 1,000 (a few queries per batch), each batch written in its own transaction.
- The checkpoint is the last QID written. `--resume` continues after it, so an interrupted run loses at most one batch.
- Re-importing a film updates it in place and keeps its UUID: the record is keyed by provider and external ID.
- No API key, so nothing secret can reach the web bundle or the logs.

## Import plan

| Step | Command (from `apps/api`) | Notes |
| --- | --- | --- |
| 1. Schema | `cinebase migrate` | Alembic; safe to rerun |
| 2. Trial | `cinebase import wikidata --limit 2000` | A few minutes; checks the network and mapping |
| 3. Full import | `cinebase import wikidata` | About 70–80 minutes for 430k items on a home connection; ~2 GB database |
| 4. Resume | `cinebase import wikidata --resume` | After a failure or Ctrl-C |
| 5. Collections | `cinebase link-collections` | Points the editorial home rows at catalog films by title and year |
| 6. Refresh | Repeat step 3 | Updates changed films; new Wikidata films are added |

Not done yet:

- scheduled refresh;
- removing films that Wikidata deletes;
- merging duplicate films across providers (the spec forbids merging on title and year alone).

## Sources

- Letterboxd: [terms of use](https://letterboxd.com/terms), [API access](https://letterboxd.com/api-beta/)
- TMDB: [API FAQ](https://developer.themoviedb.org/docs/faq), [terms of use](https://www.themoviedb.org/terms-of-use)
- IMDb: [non-commercial datasets](https://developer.imdb.com/non-commercial-datasets), [using IMDb data](https://help.imdb.com/article/imdb/general-information/can-i-use-imdb-data-in-my-software/G5JTRESSHJBBHTGX)
- Wikidata: [data licence (CC0)](https://www.wikidata.org/wiki/Wikidata:Licensing), [Query Service user manual](https://www.mediawiki.org/wiki/Wikidata_Query_Service/User_Manual)
- Wikimedia: [User-Agent policy](https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy), [Commons licensing](https://commons.wikimedia.org/wiki/Commons:Licensing)
