import { FilmGrid, FilmGridItem, type Density } from "@/components/film/FilmGrid";
import styles from "./SkeletonGrid.module.css";

export function SkeletonGrid({ count = 12, density = "comfortable" }: { count?: number; density?: Density }) {
  return (
    <div aria-hidden="true" data-loading-placeholder="">
      <FilmGrid density={density}>
        {Array.from({ length: count }, (_, i) => (
          <FilmGridItem key={i}>
            <div className={styles.poster} />
            <div className={styles.line} />
            <div className={`${styles.line} ${styles.short}`} />
          </FilmGridItem>
        ))}
      </FilmGrid>
    </div>
  );
}
