import styles from "@/components/film/FilmPage.module.css";

export default function FilmLoading() {
  return (
    <div className={styles.film} aria-busy="true" aria-label="Loading film">
      <div className={styles.backSkeleton} />
      <div className={styles.layout}>
        <div className={styles.posterCol}>
          <div className={styles.posterSkeleton} />
        </div>
        <div className={styles.header}>
          <div className={`${styles.lineSkeleton} ${styles.titleSkeleton}`} />
          <div className={styles.lineSkeleton} />
          <div className={`${styles.lineSkeleton} ${styles.shortSkeleton}`} />
        </div>
      </div>
    </div>
  );
}
