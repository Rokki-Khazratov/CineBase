import type { ReactNode } from "react";
import styles from "./StatePanel.module.css";

type StatePanelProps = {
  tone?: "neutral" | "error";
  title: string;
  children?: ReactNode;
  actions?: ReactNode;
  headingLevel?: "h1" | "h2";
};

/** Shared layout for empty, error and not-found states: a clear headline, why it happened, and a way forward. */
export function StatePanel({ tone = "neutral", title, children, actions, headingLevel: Heading = "h2" }: StatePanelProps) {
  return (
    <section className={`${styles.panel} ${tone === "error" ? styles.error : ""}`} role={tone === "error" ? "alert" : undefined}>
      <svg className={styles.icon} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
        {tone === "error" ? (
          <>
            <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeWidth="1.6" />
            <path d="M12 7.5v5.5M12 16.2v.3" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
          </>
        ) : (
          <>
            <circle cx="10.5" cy="10.5" r="6" fill="none" stroke="currentColor" strokeWidth="1.6" />
            <path d="m15 15 5 5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
          </>
        )}
      </svg>
      <Heading className={styles.title}>{title}</Heading>
      {children ? <div className={styles.body}>{children}</div> : null}
      {actions ? <div className={styles.actions}>{actions}</div> : null}
    </section>
  );
}
