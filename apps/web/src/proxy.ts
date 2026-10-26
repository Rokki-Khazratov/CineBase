import { NextResponse, type NextRequest } from "next/server";
import { catalogMeta } from "@/catalog";

const knownIds = new Set(catalogMeta.ids());

/**
 * Film pages are prerendered for every catalog ID. An unknown ID would otherwise get the streamed
 * not-found page with status 200. A rewrite cannot set the status, so it points at a path with no route,
 * which Next.js answers with the root not-found page and a real 404 (TECHNICAL_SPEC §5).
 */
export function proxy(request: NextRequest) {
  const id = decodeURIComponent(request.nextUrl.pathname.slice("/movies/".length));
  if (knownIds.has(id)) return NextResponse.next();
  return NextResponse.rewrite(new URL("/_film-not-found", request.url));
}

export const config = { matcher: "/movies/:id" };
