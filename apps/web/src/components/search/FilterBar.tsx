"use client";

import type { GenreRef, MovieQuery, Sort } from "@/catalog";
import {
  DECADES,
  RUNTIME_PRESETS,
  SORT_LABELS,
  decadeLabel,
  decadeRange,
  decadeValue,
  hasActiveFilters,
  yearRangeLabel,
} from "@/lib/results-url";
import styles from "./FilterBar.module.css";

type FilterBarProps = {
  query: MovieQuery;
  genres: GenreRef[];
  onChange: (changes: Partial<MovieQuery>) => void;
};

/** Genre chips plus three compact selects. Every control is a native element, so it works with keyboard and screen readers as-is. */
export function FilterBar({ query, genres, onChange }: FilterBarProps) {
  const decade = decadeValue(query);
  const runtimeIsPreset = query.runtime_max === null || (RUNTIME_PRESETS as readonly number[]).includes(query.runtime_max);
  const sorts: Sort[] = query.q ? ["relevance", "release_desc", "title_asc", "runtime_asc"] : ["release_desc", "title_asc", "runtime_asc"];

  const toggleGenre = (slug: string) => {
    const next = query.genres.includes(slug) ? query.genres.filter((g) => g !== slug) : [...query.genres, slug].sort();
    onChange({ genres: next });
  };

  return (
    <div className={styles.bar}>
      <div className={styles.chipsRow} role="group" aria-labelledby="genre-label">
        <span id="genre-label" className={styles.groupLabel}>
          Genre
        </span>
        <div className={styles.chips}>
          {genres.map((g) => (
            <button
              key={g.slug}
              type="button"
              className={styles.chip}
              aria-pressed={query.genres.includes(g.slug)}
              onClick={() => toggleGenre(g.slug)}
            >
              {g.name}
            </button>
          ))}
        </div>
      </div>

      <div className={styles.selects}>
        <label className={styles.select}>
          <span className={styles.selectLabel}>Released</span>
          <select
            value={decade}
            onChange={(e) => {
              const v = e.target.value;
              if (v === "custom") return;
              onChange(v ? decadeRange(Number(v)) : { year_from: null, year_to: null });
            }}
          >
            <option value="">Any year</option>
            {DECADES.map((d) => (
              <option key={d} value={d}>
                {decadeLabel(d)}
              </option>
            ))}
            {decade === "custom" ? <option value="custom">{yearRangeLabel(query.year_from, query.year_to)}</option> : null}
          </select>
        </label>

        <label className={styles.select}>
          <span className={styles.selectLabel}>Length</span>
          <select
            value={query.runtime_max === null ? "" : String(query.runtime_max)}
            onChange={(e) => onChange({ runtime_max: e.target.value ? Number(e.target.value) : null })}
          >
            <option value="">Any length</option>
            {RUNTIME_PRESETS.map((m) => (
              <option key={m} value={m}>
                {m} min or less
              </option>
            ))}
            {!runtimeIsPreset ? <option value={query.runtime_max!}>{query.runtime_max} min or less</option> : null}
          </select>
        </label>

        <label className={styles.select}>
          <span className={styles.selectLabel}>Sort</span>
          <select value={query.sort} onChange={(e) => onChange({ sort: e.target.value as Sort })}>
            {sorts.map((s) => (
              <option key={s} value={s}>
                {SORT_LABELS[s]}
              </option>
            ))}
          </select>
        </label>

        {hasActiveFilters(query) ? (
          <button
            type="button"
            className={styles.clearAll}
            onClick={() => onChange({ genres: [], year_from: null, year_to: null, runtime_max: null })}
          >
            Clear filters
          </button>
        ) : null}
      </div>
    </div>
  );
}
