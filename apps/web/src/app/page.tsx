import Link from "next/link";
import { catalog, catalogMeta } from "@/catalog";
import { CollectionRow, GenreLinks } from "@/components/home/CollectionRow";
import { HeroSearch } from "@/components/home/HeroSearch";
import styles from "@/components/home/Home.module.css";

const EXAMPLES = ["Nosferatu", "Сталкер", "Dune (2021)", "8½", "Fabuleux destin"];

export default async function HomePage() {
  const discover = await catalog.getDiscover();
  return (
    <div className={styles.home}>
      <section className={styles.hero} aria-labelledby="home-title">
        <p className={styles.eyebrow}>Film catalog prototype</p>
        <h1 id="home-title" className={styles.heroTitle}>
          Find the film you mean.
        </h1>
        <p className={styles.heroText}>
          Search by title, original title or another known title. Remakes and films that share a name are told apart by
          year and director.
        </p>
        <HeroSearch />
        <ul className={styles.examples} aria-label="Example searches">
          <li aria-hidden="true">Try</li>
          {EXAMPLES.map((q) => (
            <li key={q}>
              <Link href={`/movies?q=${encodeURIComponent(q)}`} className={styles.example}>
                {q}
              </Link>
            </li>
          ))}
        </ul>
      </section>
      {discover.blocks.map((block) => (
        <CollectionRow key={block.slug} block={block} />
      ))}
      <GenreLinks genres={catalogMeta.genres()} />
    </div>
  );
}
