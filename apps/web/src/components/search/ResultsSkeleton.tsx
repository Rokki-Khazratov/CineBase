import type { CatalogInfo } from "@/catalog";
import { SkeletonGrid } from "@/components/states/SkeletonGrid";
import { ResultsHeader } from "./ResultsHeader";
import styles from "./ResultsView.module.css";

/** Server-rendered placeholder with the same geometry as the toolbar, shown until the search state is read from the URL. */
export function ResultsSkeleton({ info }: { info: CatalogInfo }) {
  return (
    <div className={styles.page}>
      <ResultsHeader info={info} />
      <div className={styles.toolbar} aria-hidden="true">
        <div className={styles.skeletonField} />
        <div className={styles.skeletonSelects} />
      </div>
      <div className={styles.summary}>
        <p className={styles.count}>Loading films…</p>
      </div>
      <SkeletonGrid />
    </div>
  );
}
