import type { ReactNode } from "react";
import styles from "./FilmGrid.module.css";

export type Density = "comfortable" | "compact";

export function FilmGrid({ children, density = "comfortable", label }: { children: ReactNode; density?: Density; label?: string }) {
  return (
    <ul className={`${styles.grid} ${styles[density]}`} aria-label={label}>
      {children}
    </ul>
  );
}

export function FilmGridItem({ children }: { children: ReactNode }) {
  return <li className={styles.item}>{children}</li>;
}
