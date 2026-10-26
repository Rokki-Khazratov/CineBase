import Link from "next/link";
import type { MovieSummary } from "@/catalog";
import { directorNames, yearLabel } from "./format";
import { Poster } from "./Poster";
import styles from "./FilmCard.module.css";

type FilmCardProps = {
  movie: MovieSummary;
  priority?: boolean;
  onOpen?: (movie: MovieSummary) => void;
  headingLevel?: "h2" | "h3";
};

/** Title, year and director: enough to tell remakes apart at a glance (U2). */
export function FilmCard({ movie, priority, onOpen, headingLevel: Heading = "h3" }: FilmCardProps) {
  return (
    <article className={styles.card}>
      <Link href={`/movies/${movie.id}`} className={styles.link} onClick={onOpen ? () => onOpen(movie) : undefined}>
        <Poster poster={movie.poster} title={movie.title} decorative priority={priority} />
        <div className={styles.body}>
          <Heading className={styles.title}>{movie.title}</Heading>
          <p className={styles.meta}>
            <span className={styles.year}>{yearLabel(movie)}</span>
            <span aria-hidden="true"> · </span>
            <span className="visually-hidden">, directed by </span>
            <span>{directorNames(movie.directors)}</span>
          </p>
        </div>
      </Link>
    </article>
  );
}
