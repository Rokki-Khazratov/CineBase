import styles from "./ResultsView.module.css";

export function ResultsHeader({ movieCount }: { movieCount: number }) {
  return (
    <header className={styles.head}>
      <h1 className={styles.title}>Find a film</h1>
      <p className={styles.coverage}>
        Searching the {movieCount} films in this prototype catalog by title, original title and other known titles.
      </p>
    </header>
  );
}
