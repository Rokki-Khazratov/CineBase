import styles from "./SiteFooter.module.css";

export function SiteFooter() {
  return (
    <footer className={styles.footer}>
      <div className={styles.inner}>
        <p>
          CineBase prototype. Catalog data is a hand-made fixture set; posters are generated placeholders, not studio
          artwork.
        </p>
      </div>
    </footer>
  );
}
