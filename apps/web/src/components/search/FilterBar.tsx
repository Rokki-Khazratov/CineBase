"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { EXCLUSIONS, type Exclusion, type GenreRef, type MovieQuery, type Sort } from "@/catalog";
import {
  DECADES,
  EXCLUSION_LABELS,
  NO_FILTERS,
  RUNTIME_PRESETS,
  SORT_LABELS,
  decadeLabel,
  decadeRange,
  decadeValue,
  hasActiveFilters,
  sortOptions,
  yearRangeLabel,
} from "@/lib/results-url";
import styles from "./FilterBar.module.css";

/** A change, or a function of the latest query for changes that depend on it (several quick clicks in a row). */
export type QueryChange = Partial<MovieQuery> | ((latest: MovieQuery) => Partial<MovieQuery>);

type FilterBarProps = {
  query: MovieQuery;
  genres: GenreRef[];
  onChange: (change: QueryChange) => void;
};

function toggle<T extends string>(list: T[], value: T): T[] {
  return list.includes(value) ? list.filter((v) => v !== value) : [...list, value].sort();
}

/**
 * A disclosure menu built on <details>: it opens and closes with keyboard and screen readers as-is. Clicking
 * outside or pressing Escape closes it, like a native select.
 */
function Menu({ label, summary, active, children }: { label: string; summary: string; active: boolean; children: ReactNode }) {
  const ref = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    const details = ref.current;
    if (!details) return;
    // On "click", not "pointerdown": on a phone the open list is in the page flow, and closing it before the
    // tap ends would move the control under the finger.
    const onOutside = (e: MouseEvent) => {
      if (details.open && !details.contains(e.target as Node)) details.open = false;
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && details.open) {
        details.open = false;
        details.querySelector("summary")?.focus();
      }
    };
    document.addEventListener("click", onOutside);
    details.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("click", onOutside);
      details.removeEventListener("keydown", onKey);
    };
  }, []);
  return (
    <details ref={ref} className={styles.menu}>
      <summary className={`${styles.control} ${active ? styles.active : ""}`}>
        <span className={styles.controlLabel}>{label}</span>
        <span className={styles.controlValue}>{summary}</span>
      </summary>
      <div className={styles.panel}>{children}</div>
    </details>
  );
}

/**
 * The "Browse by" row: decade, genre, length, sort and what to hide. Selects are native; the two multi-choice
 * menus are checkboxes inside a disclosure, so every control works with keyboard and screen readers.
 */
export function FilterBar({ query, genres, onChange }: FilterBarProps) {
  const decade = decadeValue(query);
  const runtimeIsPreset = query.runtime_max === null || (RUNTIME_PRESETS as readonly number[]).includes(query.runtime_max);
  const genreNames = query.genres.map((slug) => genres.find((g) => g.slug === slug)?.name ?? slug);
  const genreSummary = genreNames.length === 0 ? "Any" : genreNames.length === 1 ? genreNames[0] : `${genreNames[0]} +${genreNames.length - 1}`;
  const hideSummary = query.exclude.length === 0 ? "Nothing" : `${query.exclude.length} selected`;

  return (
    <div className={styles.bar} role="group" aria-labelledby="browse-label">
      <span id="browse-label" className={styles.browseLabel}>
        Browse by
      </span>
      <div className={styles.controls}>
        <label className={styles.control}>
          <span className={styles.controlLabel}>Decade</span>
          <select
            value={decade}
            onChange={(e) => {
              const v = e.target.value;
              if (v === "custom") return;
              onChange(v ? decadeRange(Number(v)) : { year_from: null, year_to: null });
            }}
          >
            <option value="">Any</option>
            {DECADES.map((d) => (
              <option key={d} value={d}>
                {decadeLabel(d)}
              </option>
            ))}
            {decade === "custom" ? <option value="custom">{yearRangeLabel(query.year_from, query.year_to)}</option> : null}
          </select>
        </label>

        <Menu label="Genre" summary={genreSummary} active={query.genres.length > 0}>
          <fieldset className={styles.options}>
            <legend className="visually-hidden">Genres to show</legend>
            {genres.map((g) => (
              <label key={g.slug} className={styles.option}>
                <input
                  type="checkbox"
                  checked={query.genres.includes(g.slug)}
                  onChange={() => onChange((latest) => ({ genres: toggle(latest.genres, g.slug) }))}
                />
                {g.name}
              </label>
            ))}
          </fieldset>
          {query.genres.length > 0 ? (
            <button type="button" className={styles.panelAction} onClick={() => onChange({ genres: [] })}>
              Any genre
            </button>
          ) : null}
        </Menu>

        <label className={styles.control}>
          <span className={styles.controlLabel}>Length</span>
          <select
            value={query.runtime_max === null ? "" : String(query.runtime_max)}
            onChange={(e) => onChange({ runtime_max: e.target.value ? Number(e.target.value) : null })}
          >
            <option value="">Any</option>
            {RUNTIME_PRESETS.map((m) => (
              <option key={m} value={m}>
                {m} min or less
              </option>
            ))}
            {!runtimeIsPreset ? <option value={query.runtime_max!}>{query.runtime_max} min or less</option> : null}
          </select>
        </label>

        <Menu label="Hide" summary={hideSummary} active={query.exclude.length > 0}>
          <fieldset className={styles.options}>
            <legend className="visually-hidden">Films to hide</legend>
            {EXCLUSIONS.map((x: Exclusion) => (
              <label key={x} className={styles.option}>
                <input
                  type="checkbox"
                  checked={query.exclude.includes(x)}
                  onChange={() => onChange((latest) => ({ exclude: toggle(latest.exclude, x) }))}
                />
                {EXCLUSION_LABELS[x]}
              </label>
            ))}
          </fieldset>
        </Menu>

        <label className={`${styles.control} ${styles.sort}`}>
          <span className={styles.controlLabel}>Sort by</span>
          <select value={query.sort} onChange={(e) => onChange({ sort: e.target.value as Sort })}>
            {sortOptions(query.q).map((s) => (
              <option key={s} value={s}>
                {SORT_LABELS[s]}
              </option>
            ))}
          </select>
        </label>

        {hasActiveFilters(query) ? (
          <button type="button" className={styles.clearAll} onClick={() => onChange(NO_FILTERS)}>
            Clear filters
          </button>
        ) : null}
      </div>
    </div>
  );
}
