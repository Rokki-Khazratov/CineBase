import { NextResponse, type NextRequest } from "next/server";
import { CATALOG_SOURCE } from "@/catalog";
import { loadFixtureData } from "@/catalog/fixture-data";

const API_URL = (process.env.CINEBASE_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;

const fixtureIds = CATALOG_SOURCE === "fixtures" ? new Set(loadFixtureData().movies.map((m) => m.id)) : null;

/** IDs the API has confirmed, so repeat visits skip the lookup. Bounded so it cannot grow without limit. */
const confirmed = new Set<string>();
const MAX_CONFIRMED = 5000;

async function exists(id: string): Promise<boolean> {
  if (fixtureIds) return fixtureIds.has(id);
  if (!UUID.test(id)) return false;
  if (confirmed.has(id)) return true;
  try {
    const response = await fetch(`${API_URL}/api/v1/movies/${id}`, { method: "GET", signal: AbortSignal.timeout(3000) });
    if (response.status === 404) return false;
    if (response.ok) {
      if (confirmed.size >= MAX_CONFIRMED) confirmed.clear();
      confirmed.add(id);
    }
  } catch {
    // The API is unreachable: let the page render so it can show its own error state.
  }
  return true;
}

/**
 * An unknown film ID would otherwise get the streamed not-found page with status 200. A rewrite cannot set
 * the status, so it points at a path with no route, which Next.js answers with the root not-found page and a
 * real 404 (TECHNICAL_SPEC §5).
 */
export async function proxy(request: NextRequest) {
  const id = decodeURIComponent(request.nextUrl.pathname.slice("/movies/".length));
  if (await exists(id)) return NextResponse.next();
  return NextResponse.rewrite(new URL("/_film-not-found", request.url));
}

export const config = { matcher: "/movies/:id" };
