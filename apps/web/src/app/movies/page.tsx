import type { Metadata } from "next";
import { Suspense } from "react";
import { getCatalogInfo, getGenres } from "@/catalog/server";
import { ResultsSkeleton } from "@/components/search/ResultsSkeleton";
import { ResultsView } from "@/components/search/ResultsView";

export const metadata: Metadata = { title: "Films" };

export default async function MoviesPage() {
  const [info, genres] = await Promise.all([getCatalogInfo(), getGenres()]);
  // The search state lives in the URL, which is only known per request; the shell around it is static.
  return (
    <Suspense fallback={<ResultsSkeleton info={info} />}>
      <ResultsView genres={genres} info={info} />
    </Suspense>
  );
}
