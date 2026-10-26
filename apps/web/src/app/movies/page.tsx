import type { Metadata } from "next";
import { Suspense } from "react";
import { catalogMeta } from "@/catalog";
import { ResultsSkeleton } from "@/components/search/ResultsSkeleton";
import { ResultsView } from "@/components/search/ResultsView";

export const metadata: Metadata = { title: "Find a film" };

export default function MoviesPage() {
  // The search state lives in the URL, which is only known per request; the shell around it is static.
  return (
    <Suspense fallback={<ResultsSkeleton movieCount={catalogMeta.movieCount} />}>
      <ResultsView genres={catalogMeta.genres()} movieCount={catalogMeta.movieCount} />
    </Suspense>
  );
}
