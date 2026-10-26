"use client";

import Form from "next/form";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Logo } from "./Logo";
import styles from "./SiteHeader.module.css";

/**
 * Search placement (see docs/verification/phase-1.md): Home has a hero search and
 * /movies has its own toolbar, so the compact header search appears on every other page.
 */
export function SiteHeader() {
  const pathname = usePathname();
  const showSearch = pathname !== "/" && pathname !== "/movies";

  return (
    <header className={styles.header}>
      <div className={styles.inner}>
        <Link href="/" className={styles.home} aria-label="CineBase home">
          <Logo />
        </Link>
        <nav aria-label="Main" className={styles.nav}>
          <Link href="/movies" className={styles.navLink} aria-current={pathname === "/movies" ? "page" : undefined}>
            Browse films
          </Link>
        </nav>
        {showSearch ? (
          <Form action="/movies" role="search" className={styles.search}>
            <label htmlFor="header-search" className="visually-hidden">
              Search films
            </label>
            <svg className={styles.icon} viewBox="0 0 20 20" aria-hidden="true" focusable="false">
              <circle cx="8.5" cy="8.5" r="5.5" fill="none" stroke="currentColor" strokeWidth="2" />
              <path d="m13 13 4.5 4.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
            <input id="header-search" name="q" type="search" placeholder="Search films" maxLength={200} autoComplete="off" />
          </Form>
        ) : null}
      </div>
    </header>
  );
}
