import styles from "./Logo.module.css";

/** Placeholder wordmark. Swap this component when the brand identity is decided. */
export function Logo() {
  return (
    <span className={styles.logo}>
      <svg className={styles.mark} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
        <rect x="2" y="4" width="20" height="16" rx="3" fill="currentColor" />
        <rect x="5" y="7" width="3" height="3" rx="0.75" fill="var(--color-surface)" />
        <rect x="5" y="14" width="3" height="3" rx="0.75" fill="var(--color-surface)" />
        <rect x="16" y="7" width="3" height="3" rx="0.75" fill="var(--color-surface)" />
        <rect x="16" y="14" width="3" height="3" rx="0.75" fill="var(--color-surface)" />
      </svg>
      <span className={styles.word}>CineBase</span>
    </span>
  );
}
