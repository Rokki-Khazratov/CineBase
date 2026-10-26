import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { catalog, catalogMeta, CatalogError, type Credit, type MovieDetail } from "@/catalog";
import { BackLink } from "@/components/film/BackLink";
import { FilmCard } from "@/components/film/FilmCard";
import { FilmGrid, FilmGridItem } from "@/components/film/FilmGrid";
import { directorNames, languageName, localeLabel, releaseLabel, runtimeLabel, yearLabel } from "@/components/film/format";
import { Poster } from "@/components/film/Poster";
import styles from "@/components/film/FilmPage.module.css";
import { otherVersions } from "@/lib/other-versions";

export function generateStaticParams() {
  return catalogMeta.ids().map((id) => ({ id }));
}

async function loadMovie(id: string): Promise<MovieDetail> {
  try {
    return await catalog.getMovie(id);
  } catch (err) {
    if (err instanceof CatalogError && err.status === 404) notFound();
    throw err;
  }
}

export async function generateMetadata({ params }: PageProps<"/movies/[id]">): Promise<Metadata> {
  const { id } = await params;
  try {
    const movie = await catalog.getMovie(id);
    return {
      title: movie.year ? `${movie.title} (${movie.year})` : movie.title,
      description: movie.synopsis ?? undefined,
    };
  } catch {
    return { title: "Film not found" };
  }
}

function groupCrew(crew: Credit[]): { job: string; names: string[] }[] {
  const groups = new Map<string, string[]>();
  for (const c of crew) {
    const names = groups.get(c.job) ?? [];
    if (!names.includes(c.person.name)) names.push(c.person.name);
    groups.set(c.job, names);
  }
  return [...groups].map(([job, names]) => ({ job, names }));
}

export default async function FilmPage({ params }: PageProps<"/movies/[id]">) {
  const { id } = await params;
  const movie = await loadMovie(id);
  const [credits, others] = await Promise.all([catalog.getCredits(id), otherVersions(movie)]);
  const runtime = runtimeLabel(movie.runtime_minutes);
  const crew = groupCrew(credits.crew);
  const language = languageName(movie.original_language);

  return (
    <article className={styles.film}>
      <BackLink filmId={movie.id} />

      <div className={styles.layout}>
        <div className={styles.posterCol}>
          <Poster poster={movie.poster} title={movie.title} priority sizes="detail" />
          {movie.poster ? <p className={styles.posterNote}>Illustrative poster made for this prototype, not the official artwork.</p> : null}
        </div>

        <header className={styles.header}>
          {movie.release.status === "announced" ? <p className={styles.badge}>Announced · not yet released</p> : null}
          <h1 className={styles.title}>{movie.title}</h1>
          {movie.original_title ? (
            <p className={styles.originalTitle} lang={movie.original_language ?? undefined}>
              {movie.original_title}
            </p>
          ) : null}
          <p className={styles.facts}>
            <span>{yearLabel(movie)}</span>
            <span aria-hidden="true">·</span>
            <span>{runtime ?? "Runtime unknown"}</span>
            {movie.genres.length > 0 ? (
              <>
                <span aria-hidden="true">·</span>
                <span className={styles.genres}>
                  {movie.genres.map((g, i) => (
                    <span key={g.slug}>
                      <Link href={`/movies?genre=${g.slug}`}>{g.name}</Link>
                      {i < movie.genres.length - 1 ? ", " : ""}
                    </span>
                  ))}
                </span>
              </>
            ) : null}
          </p>
          <p className={styles.directed}>
            Directed by <strong>{directorNames(movie.directors)}</strong>
          </p>
        </header>

        <div className={styles.main}>
          <section aria-labelledby="synopsis-heading" className={styles.section}>
            <h2 id="synopsis-heading" className={styles.sectionTitle}>
              Synopsis
            </h2>
            <p className={styles.synopsis}>{movie.synopsis ?? "No synopsis yet."}</p>
          </section>

          <div className={styles.credits}>
            <section aria-labelledby="cast-heading" className={styles.section}>
              <h2 id="cast-heading" className={styles.sectionTitle}>
                Cast
              </h2>
              {credits.cast.length > 0 ? (
                <ul className={styles.creditList}>
                  {credits.cast.map((c) => (
                    <li key={`${c.person.id}-${c.order}`}>
                      <span className={styles.person}>{c.person.name}</span>
                      {c.character ? <span className={styles.role}>{c.character}</span> : null}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className={styles.muted}>No cast listed yet.</p>
              )}
            </section>

            <section aria-labelledby="crew-heading" className={styles.section}>
              <h2 id="crew-heading" className={styles.sectionTitle}>
                Crew
              </h2>
              <dl className={styles.crewList}>
                {crew.map((g) => (
                  <div key={g.job}>
                    <dt>{g.job}</dt>
                    <dd>{g.names.join(", ")}</dd>
                  </div>
                ))}
              </dl>
            </section>
          </div>

          <section aria-labelledby="details-heading" className={styles.section}>
            <h2 id="details-heading" className={styles.sectionTitle}>
              Details
            </h2>
            <dl className={styles.details}>
              <div>
                <dt>{movie.release.status === "announced" ? "Release" : "Released"}</dt>
                <dd>{releaseLabel(movie.release, movie.year)}</dd>
              </div>
              <div>
                <dt>Runtime</dt>
                <dd>{runtime ? `${runtime} (${movie.runtime_minutes} min)` : "Unknown"}</dd>
              </div>
              <div>
                <dt>Original language</dt>
                <dd>{language ?? "Unknown"}</dd>
              </div>
              {movie.alternate_titles.length > 0 ? (
                <div>
                  <dt>Also known as</dt>
                  <dd>
                    <ul className={styles.akaList}>
                      {movie.alternate_titles.map((a) => (
                        <li key={a.title}>
                          {a.title}
                          {a.locale ? <span className={styles.muted}> · {localeLabel(a.locale)}</span> : null}
                        </li>
                      ))}
                    </ul>
                  </dd>
                </div>
              ) : null}
              <div>
                <dt>Source</dt>
                <dd>
                  {movie.provenance.sources.map((s) => `${s.name} ${s.external_id}`).join(", ")}
                  <span className={styles.muted}> · catalog version {movie.provenance.catalog_version}</span>
                </dd>
              </div>
            </dl>
          </section>
        </div>
      </div>

      {others.length > 0 ? (
        <section aria-labelledby="others-heading" className={styles.others}>
          <h2 id="others-heading" className={styles.sectionTitle}>
            Other films with this title
          </h2>
          <p className={styles.muted}>Remakes, earlier versions and films that share a name, told apart by year and director.</p>
          <FilmGrid density="compact" label="Other films with this title">
            {others.map((m) => (
              <FilmGridItem key={m.id}>
                <FilmCard movie={m} />
              </FilmGridItem>
            ))}
          </FilmGrid>
        </section>
      ) : null}
    </article>
  );
}
