/**
 * Back-navigation backup for the results page (U4). Next.js normally keeps the page mounted while you
 * view a film, so state survives on its own; this snapshot covers the cases where the page is rebuilt
 * (route evicted from the router cache, full page load, history restored after closing the tab).
 */
import type { MovieSummary } from "@/catalog";

const SNAPSHOT_KEY = "cinebase:results-snapshot";
const RETURN_KEY = "cinebase:return-to-results";

export type ResultsSnapshot = {
  key: string;
  items: MovieSummary[];
  nextCursor: string | null;
  hasMore: boolean;
  scrollY: number;
};

function storage(): Storage | null {
  try {
    return typeof window === "undefined" ? null : window.sessionStorage;
  } catch {
    return null;
  }
}

export function saveSnapshot(snapshot: ResultsSnapshot): void {
  try {
    storage()?.setItem(SNAPSHOT_KEY, JSON.stringify(snapshot));
  } catch {
    // Quota or privacy mode: Back still works through the mounted page, only the fallback is lost.
  }
}

export function readSnapshot(key: string): ResultsSnapshot | null {
  try {
    const raw = storage()?.getItem(SNAPSHOT_KEY);
    if (!raw) return null;
    const snapshot = JSON.parse(raw) as ResultsSnapshot;
    return snapshot.key === key && Array.isArray(snapshot.items) ? snapshot : null;
  } catch {
    return null;
  }
}

/** Remembers that the user left the results page for a film, and where to return. */
export function markLeftForFilm(filmId: string, resultsHref: string): void {
  try {
    storage()?.setItem(RETURN_KEY, JSON.stringify({ filmId, resultsHref }));
  } catch {
    // ignore
  }
}

export type ReturnTarget = { filmId: string; resultsHref: string };

/** Raw stored string, stable between calls, for useSyncExternalStore. */
export function readReturnTargetRaw(): string | null {
  try {
    return storage()?.getItem(RETURN_KEY) ?? null;
  } catch {
    return null;
  }
}

export function parseReturnTarget(raw: string | null): ReturnTarget | null {
  if (!raw) return null;
  try {
    const value = JSON.parse(raw) as ReturnTarget;
    return typeof value.filmId === "string" && typeof value.resultsHref === "string" && value.resultsHref.startsWith("/movies")
      ? value
      : null;
  } catch {
    return null;
  }
}

export function readReturnTarget(): ReturnTarget | null {
  return parseReturnTarget(readReturnTargetRaw());
}

/**
 * Returns the saved results for this query when the user is coming back from a film, and clears the
 * return marker so a later, unrelated visit starts at the top.
 */
export function takeReturnSnapshot(key: string): ResultsSnapshot | null {
  const target = readReturnTarget();
  if (!target) return null;
  const snapshot = readSnapshot(key);
  if (!snapshot) return null;
  try {
    storage()?.removeItem(RETURN_KEY);
  } catch {
    // ignore
  }
  return snapshot;
}
