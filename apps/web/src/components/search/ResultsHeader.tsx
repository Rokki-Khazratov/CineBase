import type { CatalogInfo } from "@/catalog";
import styles from "./ResultsView.module.css";

/** Display names for the API's source keys. */
const SOURCE_LABELS: Record<string, string> = {
  wikidata: "Wikidata (CC0)",
  "cinebase-fixture": "CineBase fixtures",
};

export function ResultsHeader({ info }: { info: CatalogInfo }) {
  const sources = [...new Set((info.sources ?? []).map((s) => SOURCE_LABELS[s] ?? s))];
  return (
    <header className={styles.head}>
      <h1 className={styles.title}>Films</h1>
      <p className={styles.coverage}>
        Search by title, original title or another known title, or browse by decade, genre and length.
        {sources.length > 0 ? <span className={styles.sources}> Catalog data: {sources.join(", ")}.</span> : null}
      </p>
    </header>
  );
}
