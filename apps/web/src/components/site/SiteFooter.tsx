import { CATALOG_SOURCE } from "@/catalog";
import styles from "./SiteFooter.module.css";

export function SiteFooter() {
  return (
    <footer className={styles.footer}>
      <div className={styles.inner}>
        {CATALOG_SOURCE === "api" ? (
          <p>
            CineBase prototype. Film facts come from{" "}
            <a href="https://www.wikidata.org/" rel="external noopener">
              Wikidata
            </a>{" "}
            (CC0). Posters come from Wikimedia Commons, under the licence shown on each film page.
          </p>
        ) : (
          <p>
            CineBase prototype. Catalog data is a hand-made fixture set; posters are generated placeholders, not studio
            artwork.
          </p>
        )}
      </div>
    </footer>
  );
}
