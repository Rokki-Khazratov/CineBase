"use client";

import { forwardRef } from "react";
import { MAX_QUERY_LENGTH } from "@/catalog";
import styles from "./SearchField.module.css";

type SearchFieldProps = {
  id: string;
  value: string;
  onChange: (value: string) => void;
  onClear: () => void;
  busy?: boolean;
  size?: "large" | "regular";
  label?: string;
  autoFocus?: boolean;
};

export const SearchField = forwardRef<HTMLInputElement, SearchFieldProps>(function SearchField(
  { id, value, onChange, onClear, busy = false, size = "regular", label = "Search films by title", autoFocus },
  ref,
) {
  return (
    <div className={`${styles.field} ${size === "large" ? styles.large : ""}`}>
      <label htmlFor={id} className="visually-hidden">
        {label}
      </label>
      <svg className={styles.icon} viewBox="0 0 20 20" aria-hidden="true" focusable="false">
        <circle cx="8.5" cy="8.5" r="5.5" fill="none" stroke="currentColor" strokeWidth="2" />
        <path d="m13 13 4.5 4.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      </svg>
      <input
        ref={ref}
        id={id}
        name="q"
        type="search"
        inputMode="search"
        enterKeyHint="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Search by film title"
        maxLength={MAX_QUERY_LENGTH}
        autoComplete="off"
        autoCorrect="off"
        spellCheck={false}
        autoFocus={autoFocus}
        className={styles.input}
      />
      {busy ? <span className={styles.spinner} aria-hidden="true" /> : null}
      {value ? (
        <button type="button" className={styles.clear} onClick={onClear} aria-label="Clear search">
          <svg viewBox="0 0 20 20" aria-hidden="true" focusable="false">
            <path d="m5.5 5.5 9 9m0-9-9 9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
        </button>
      ) : null}
    </div>
  );
});
