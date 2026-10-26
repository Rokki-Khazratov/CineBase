"use client";

import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { useSearchParams } from "next/navigation";
import { catalog, CatalogError, DEFAULT_LIMIT, SIMULATED_LATENCY, type CatalogInfo, type GenreRef, type MovieQuery, type MovieSummary } from "@/catalog";
import { formatCount } from "@/components/film/format";
import { FilmCard } from "@/components/film/FilmCard";
import { FilmGrid, FilmGridItem } from "@/components/film/FilmGrid";
import { SkeletonGrid } from "@/components/states/SkeletonGrid";
import { StatePanel } from "@/components/states/StatePanel";
import buttons from "@/components/ui/Button.module.css";
import { markLeftForFilm, saveSnapshot, takeReturnSnapshot } from "@/lib/results-snapshot";
import { devOptionsFromUrl, hasActiveFilters, NO_FILTERS, queryFromUrl, resultsHref, withChanges, withDevParams } from "@/lib/results-url";
import { DensityToggle, useDensity } from "./DensityToggle";
import { FilterBar, type QueryChange } from "./FilterBar";
import { ResultsHeader } from "./ResultsHeader";
import { SearchField } from "./SearchField";
import styles from "./ResultsView.module.css";

const DEBOUNCE_MS = 250;
/** Fixture answers are instant; a small delay makes loading states behave like a real network round trip. */
const DEFAULT_LATENCY_MS = SIMULATED_LATENCY ? 180 : undefined;

type Loaded = { key: string; items: MovieSummary[]; nextCursor: string | null; hasMore: boolean; total: number | null };
type Failure = { key: string; attempt: number; error: CatalogError };

function toCatalogError(err: unknown): CatalogError {
  if (err instanceof CatalogError) return err;
  return new CatalogError(500, "unexpected_error", "Something went wrong while loading films.");
}

const films = (n: number) => `${formatCount(n)} ${n === 1 ? "film" : "films"}`;

/** "There are 1,204 films matching your filters", or a count of what is shown when the total is unknown. */
function countText(loaded: Loaded, q: string, filtered: boolean): string {
  if (loaded.total !== null) {
    if (q) return `${films(loaded.total)} found for “${q}”`;
    const verb = loaded.total === 1 ? "There is" : "There are";
    return `${verb} ${films(loaded.total)}${filtered ? " matching your filters" : ""}`;
  }
  const n = loaded.items.length;
  if (loaded.hasMore) return `Showing the first ${films(n)}${q ? ` for “${q}”` : ""}`;
  return q ? `${films(n)} found for “${q}”` : films(n);
}

export function ResultsView({ genres, info }: { genres: GenreRef[]; info: CatalogInfo }) {
  const params = useSearchParams();
  const genreSlugs = useMemo(() => new Set(genres.map((g) => g.slug)), [genres]);
  const query = useMemo(() => queryFromUrl(new URLSearchParams(params.toString()), genreSlugs), [params, genreSlugs]);
  const dev = useMemo(() => devOptionsFromUrl(new URLSearchParams(params.toString())), [params]);
  const key = resultsHref(query);
  const client = useMemo(
    () => catalog.withOptions({ latencyMs: dev.latencyMs ?? DEFAULT_LATENCY_MS, fail: dev.fail === "always" }),
    [dev.latencyMs, dev.fail],
  );
  const [density, setDensity] = useDensity();

  // The text box leads the URL by up to one debounce interval. When the URL changes from elsewhere
  // (Back/Forward, the header search), the box follows it. A value this page wrote itself is never copied
  // back, so a slow typist's newer keystrokes are not replaced by the older debounced value.
  const [input, setInput] = useState(query.q);
  const [seenQ, setSeenQ] = useState(query.q);
  const [writtenQ, setWrittenQ] = useState<string | null>(null);
  if (seenQ !== query.q) {
    setSeenQ(query.q);
    if (query.q !== writtenQ && input.trim() !== query.q) setInput(query.q);
  }

  // The controls show a change at once, before useSearchParams catches up with the new URL; otherwise a
  // checkbox would flip back for a frame. Any URL change (that one, or Back/Forward) ends the override.
  const [optimistic, setOptimistic] = useState<{ fromKey: string; query: MovieQuery } | null>(null);
  if (optimistic && optimistic.fromKey !== key) setOptimistic(null);

  const navigate = useCallback(
    (next: MovieQuery) => {
      const href = withDevParams(resultsHref(next), dev);
      setWrittenQ(next.q);
      setOptimistic(resultsHref(next) === key ? null : { fromKey: key, query: next });
      // Shallow URL update: Next.js syncs useSearchParams without a server round trip.
      if (href !== window.location.pathname + window.location.search) window.history.replaceState(null, "", href);
    },
    [dev, key],
  );

  // The address bar changes at once while the rendered `query` catches up a moment later, so every change
  // starts from the URL as it is now. Otherwise a second quick change would undo the first.
  const latestQuery = useCallback(
    () => queryFromUrl(new URLSearchParams(window.location.search), genreSlugs),
    [genreSlugs],
  );

  useEffect(() => {
    if (input.trim() === query.q) return;
    const timer = setTimeout(() => {
      const latest = latestQuery();
      if (input.trim() !== latest.q) navigate(withChanges(latest, { q: input }));
    }, DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [input, query, navigate, latestQuery]);

  const commit = (change: QueryChange) => {
    const latest = latestQuery();
    const base = input.trim() !== latest.q ? withChanges(latest, { q: input }) : latest;
    navigate(withChanges(base, typeof change === "function" ? change(base) : change));
  };

  const onSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const latest = latestQuery();
    if (input.trim() !== latest.q) navigate(withChanges(latest, { q: input }));
    // Close the on-screen keyboard so the results are visible.
    if (window.matchMedia("(pointer: coarse)").matches) (document.activeElement as HTMLElement | null)?.blur();
  };

  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const [failure, setFailure] = useState<Failure | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [more, setMore] = useState<{ key: string; failed: boolean } | null>(null);
  const seq = useRef(0);
  const loadedKey = useRef<string | null>(null);
  const moreController = useRef<AbortController | null>(null);
  const pendingScroll = useRef<number | null>(null);
  const focusIndex = useRef<number | null>(null);
  const gridRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const returning = takeReturnSnapshot(key);
    if (loadedKey.current === key) {
      // Shown again after a film page (the route stayed mounted): keep the list, put the position back.
      if (returning) pendingScroll.current = returning.scrollY;
      return;
    }
    const id = ++seq.current;
    if (returning) {
      // The page was rebuilt (reload, evicted route): use the saved pages instead of refetching only page one.
      loadedKey.current = key;
      pendingScroll.current = returning.scrollY;
      const { items, nextCursor, hasMore, total } = returning;
      queueMicrotask(() => {
        if (id === seq.current) setLoaded({ key, items, nextCursor, hasMore, total: total ?? null });
      });
      return;
    }
    const controller = new AbortController();
    const source = dev.fail === "once" && attempt === 0 ? client.withOptions({ fail: true }) : client;
    source
      .listMovies({ ...query, limit: DEFAULT_LIMIT, cursor: null }, { signal: controller.signal })
      .then((page) => {
        if (id !== seq.current) return;
        loadedKey.current = key;
        setLoaded({ key, items: page.items, nextCursor: page.next_cursor, hasMore: page.has_more, total: page.total ?? null });
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted || id !== seq.current) return;
        setFailure({ key, attempt, error: toCatalogError(err) });
      });
    return () => {
      controller.abort();
      moreController.current?.abort();
    };
  }, [key, query, client, attempt, dev.fail]);

  const current = loaded?.key === key ? loaded : null;
  const error = failure && failure.key === key && failure.attempt === attempt && !current ? failure.error : null;
  const stale = loaded !== null && !current;
  const moreState = more?.key === key ? more : null;

  useLayoutEffect(() => {
    if (pendingScroll.current !== null && current) {
      const y = pendingScroll.current;
      pendingScroll.current = null;
      window.scrollTo({ top: y, behavior: "instant" });
    }
    if (focusIndex.current !== null && current) {
      const links = gridRef.current?.querySelectorAll<HTMLAnchorElement>("a[href]");
      links?.[focusIndex.current]?.focus();
      focusIndex.current = null;
    }
  });

  const retry = () => {
    loadedKey.current = null;
    setAttempt((a) => a + 1);
  };

  const loadMore = () => {
    if (!current?.nextCursor) return;
    moreController.current?.abort();
    const controller = new AbortController();
    moreController.current = controller;
    const forKey = key;
    const firstNew = current.items.length;
    setMore({ key: forKey, failed: false });
    client
      .listMovies({ ...query, limit: DEFAULT_LIMIT, cursor: current.nextCursor }, { signal: controller.signal })
      .then((page) => {
        focusIndex.current = firstNew;
        setLoaded((prev) =>
          prev && prev.key === forKey
            ? { ...prev, items: [...prev.items, ...page.items], nextCursor: page.next_cursor, hasMore: page.has_more }
            : prev,
        );
        setMore(null);
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        const e = toCatalogError(err);
        if (e.code === "invalid_cursor") {
          // The catalog changed under the cursor: start this query again from the first page.
          setMore(null);
          retry();
          return;
        }
        setMore({ key: forKey, failed: true });
      });
  };

  const openFilm = (movie: MovieSummary) => {
    if (!current) return;
    saveSnapshot({ key, items: current.items, nextCursor: current.nextCursor, hasMore: current.hasMore, total: current.total, scrollY: window.scrollY });
    markLeftForFilm(movie.id, window.location.pathname + window.location.search);
  };

  const clearFilters = () => commit(NO_FILTERS);
  const filtersActive = hasActiveFilters(query);
  const typing = input.trim() !== query.q;

  let body: React.ReactNode;
  if (error) {
    body = (
      <StatePanel
        tone="error"
        title="Films couldn’t be loaded"
        actions={
          <button type="button" className={`${buttons.button} ${buttons.primary}`} onClick={retry}>
            Try again
          </button>
        }
      >
        <p>The catalog didn’t respond. Your search and filters are kept, so trying again picks up where you left off.</p>
        <p className={styles.errorCode}>
          Error {error.status} · {error.code}
        </p>
      </StatePanel>
    );
  } else if (!loaded || (stale && loaded.items.length === 0)) {
    body = <SkeletonGrid density={density} count={density === "compact" ? 18 : 12} />;
  } else if (loaded.items.length === 0) {
    body = (
      <StatePanel
        title={query.q ? `No films match “${query.q}”` : "No films match these filters"}
        actions={
          <>
            {filtersActive ? (
              <button type="button" className={`${buttons.button} ${buttons.primary}`} onClick={clearFilters}>
                Clear filters
              </button>
            ) : null}
            {query.q ? (
              <button
                type="button"
                className={buttons.button}
                onClick={() => {
                  setInput("");
                  commit({ q: "" });
                }}
              >
                Clear search
              </button>
            ) : null}
          </>
        }
      >
        {query.q ? (
          <ul className={styles.tips}>
            <li>Check the spelling, or try fewer words.</li>
            <li>Try the original title or another known title, for example “Сталкер” or “Le Fabuleux Destin”.</li>
            {filtersActive ? <li>Filters are on. Clearing them may show more films.</li> : null}
            <li>The catalog holds {formatCount(info.movie_count)} films, so some titles may not be in it yet.</li>
          </ul>
        ) : (
          <p>No film in the catalog has all of the selected filters. Remove one to widen the list.</p>
        )}
      </StatePanel>
    );
  } else {
    body = (
      <div ref={gridRef} className={`${styles.results} ${stale ? styles.stale : ""}`} aria-busy={stale || undefined}>
        <FilmGrid density={density} label="Films">
          {loaded.items.map((movie, i) => (
            <FilmGridItem key={movie.id}>
              <FilmCard movie={movie} priority={i < 6} onOpen={openFilm} headingLevel="h2" />
            </FilmGridItem>
          ))}
        </FilmGrid>
        {current?.hasMore ? (
          <div className={styles.more}>
            {moreState?.failed ? <p className={styles.moreError}>The next films couldn’t be loaded.</p> : null}
            <button
              type="button"
              className={buttons.button}
              onClick={loadMore}
              disabled={moreState !== null && !moreState.failed}
            >
              {moreState && !moreState.failed ? "Loading…" : moreState?.failed ? "Try again" : "Show more films"}
            </button>
          </div>
        ) : null}
      </div>
    );
  }

  const shown = optimistic?.query ?? query;
  const status = current ? countText(current, query.q, filtersActive) : error ? "Films couldn’t be loaded" : "Loading films…";

  return (
    <div className={styles.page}>
      <ResultsHeader info={info} />
      <div className={styles.toolbar}>
        <form role="search" onSubmit={onSubmit} className={styles.searchForm}>
          <SearchField
            id="results-search"
            value={input}
            onChange={setInput}
            onClear={() => {
              setInput("");
              commit({ q: "" });
            }}
            busy={typing || stale}
            size="large"
          />
        </form>
        <FilterBar query={typing ? withChanges(shown, { q: input }) : shown} genres={genres} onChange={commit} />
      </div>
      <div className={styles.summary}>
        <p className={styles.count} aria-live="polite" aria-atomic="true">
          {status}
        </p>
        <DensityToggle density={density} onChange={setDensity} />
      </div>
      {body}
    </div>
  );
}
