"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useSyncExternalStore, type MouseEvent } from "react";
import { parseReturnTarget, readReturnTargetRaw } from "@/lib/results-snapshot";
import styles from "./FilmPage.module.css";

const noopSubscribe = () => () => {};

/**
 * "Back to results" goes back in history when the user came from the results page, so the list, filters
 * and scroll position are exactly as they left them. Opened directly, it links to the results page instead.
 */
export function BackLink({ filmId }: { filmId: string }) {
  const router = useRouter();
  const target = parseReturnTarget(useSyncExternalStore(noopSubscribe, readReturnTargetRaw, () => null));
  const href = target?.resultsHref ?? "/movies";
  const cameFromResults = target?.filmId === filmId;

  const onClick = (e: MouseEvent<HTMLAnchorElement>) => {
    if (!cameFromResults || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || window.history.length < 2) return;
    e.preventDefault();
    router.back();
  };

  return (
    <Link href={href} onClick={onClick} className={styles.back}>
      <svg viewBox="0 0 20 20" aria-hidden="true" focusable="false">
        <path d="M12.5 4.5 7 10l5.5 5.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      {target ? "Back to results" : "Browse all films"}
    </Link>
  );
}
