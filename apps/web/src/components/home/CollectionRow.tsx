import Link from "next/link";
import type { DiscoverBlock } from "@/catalog";
import { FilmCard } from "@/components/film/FilmCard";
import styles from "./Home.module.css";

export function CollectionRow({ block }: { block: DiscoverBlock }) {
  const headingId = `collection-${block.slug}`;
  return (
    <section className={styles.collection} aria-labelledby={headingId}>
      <div className={styles.collectionHead}>
        <div>
          <h2 id={headingId} className={styles.sectionTitle}>
            {block.title}
          </h2>
          <p className={styles.sectionText}>{block.description}</p>
        </div>
        <span className={styles.collectionCount}>{block.movie_count} films</span>
      </div>
      {/* Horizontally scrolling row; it is focusable so keyboard users can scroll it too. */}
      <ul className={styles.row} tabIndex={0} aria-label={`${block.title}, ${block.movie_count} films`}>
        {block.items.map((movie) => (
          <li key={movie.id} className={styles.rowItem}>
            <FilmCard movie={movie} headingLevel="h3" />
          </li>
        ))}
      </ul>
    </section>
  );
}

export function GenreLinks({ genres }: { genres: { slug: string; name: string }[] }) {
  return (
    <section className={styles.genres} aria-labelledby="genres-heading">
      <h2 id="genres-heading" className={styles.sectionTitle}>
        Browse by genre
      </h2>
      <ul className={styles.genreList}>
        {genres.map((g) => (
          <li key={g.slug}>
            <Link href={`/movies?genre=${g.slug}`} className={styles.genreLink}>
              {g.name}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
