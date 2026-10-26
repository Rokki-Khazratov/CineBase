"use client";

import { useSyncExternalStore } from "react";
import type { Density } from "@/components/film/FilmGrid";
import styles from "./DensityToggle.module.css";

const STORAGE_KEY = "cinebase:density";
const EVENT = "cinebase:density-change";

function read(): Density {
  try {
    return window.localStorage.getItem(STORAGE_KEY) === "compact" ? "compact" : "comfortable";
  } catch {
    return "comfortable";
  }
}

function subscribe(callback: () => void) {
  window.addEventListener(EVENT, callback);
  window.addEventListener("storage", callback);
  return () => {
    window.removeEventListener(EVENT, callback);
    window.removeEventListener("storage", callback);
  };
}

export function useDensity(): [Density, (d: Density) => void] {
  const density = useSyncExternalStore(subscribe, read, () => "comfortable" as Density);
  const set = (d: Density) => {
    try {
      window.localStorage.setItem(STORAGE_KEY, d);
    } catch {
      // Not persisted in private mode; the choice still applies until reload.
    }
    window.dispatchEvent(new Event(EVENT));
  };
  return [density, set];
}

export function DensityToggle({ density, onChange }: { density: Density; onChange: (d: Density) => void }) {
  return (
    <div className={styles.toggle} role="group" aria-label="Card size">
      {(["comfortable", "compact"] as const).map((d) => (
        <button key={d} type="button" aria-pressed={density === d} onClick={() => onChange(d)} className={styles.option} title={d === "comfortable" ? "Larger cards" : "More films per row"}>
          <svg viewBox="0 0 20 20" aria-hidden="true" focusable="false">
            {d === "comfortable" ? (
              <>
                <rect x="3" y="3" width="6" height="14" rx="1.2" />
                <rect x="11" y="3" width="6" height="14" rx="1.2" />
              </>
            ) : (
              <>
                <rect x="2.5" y="3" width="4" height="6" rx="0.8" />
                <rect x="8" y="3" width="4" height="6" rx="0.8" />
                <rect x="13.5" y="3" width="4" height="6" rx="0.8" />
                <rect x="2.5" y="11" width="4" height="6" rx="0.8" />
                <rect x="8" y="11" width="4" height="6" rx="0.8" />
                <rect x="13.5" y="11" width="4" height="6" rx="0.8" />
              </>
            )}
          </svg>
          <span className={styles.label}>{d === "comfortable" ? "Comfortable" : "Compact"}</span>
        </button>
      ))}
    </div>
  );
}
