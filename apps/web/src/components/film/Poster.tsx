import type { Media } from "@/catalog";
import styles from "./Poster.module.css";

type PosterProps = {
  poster: Media | null;
  title: string;
  /** Inside a card the title is already announced, so the image is decorative there. */
  decorative?: boolean;
  priority?: boolean;
  sizes?: "card" | "detail";
};

/** A stable tint per title, so a row of films without art is easier to scan than identical grey cards. */
function hue(title: string): number {
  let h = 0;
  for (let i = 0; i < title.length; i++) h = (h * 31 + title.charCodeAt(i)) >>> 0;
  return h % 360;
}

/** Fixed 2:3 frame so the layout never shifts while art loads, with an intentional placeholder when art is missing. */
export function Poster({ poster, title, decorative = false, priority = false, sizes = "card" }: PosterProps) {
  return (
    <div className={`${styles.frame} ${sizes === "detail" ? styles.detail : ""}`}>
      {poster ? (
        // Fixture art is local SVG and provider art is an already-sized Commons thumbnail, so next/image
        // optimization adds nothing here.
        // eslint-disable-next-line @next/next/no-img-element
        <img
          className={styles.image}
          src={poster.url}
          alt={decorative ? "" : poster.alt}
          width={poster.width ?? undefined}
          height={poster.height ?? undefined}
          loading={priority ? "eager" : "lazy"}
          fetchPriority={priority ? "high" : "auto"}
          decoding="async"
        />
      ) : (
        <div className={styles.placeholder} style={{ "--poster-hue": hue(title) } as React.CSSProperties} role={decorative ? undefined : "img"} aria-label={decorative ? undefined : `No poster available for ${title}`} aria-hidden={decorative || undefined}>
          <svg className={styles.placeholderIcon} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <rect x="3" y="5" width="18" height="14" rx="2" fill="none" stroke="currentColor" strokeWidth="1.5" />
            <path d="M3 9h18M3 15h18M7 5v4M12 5v4M17 5v4M7 15v4M12 15v4M17 15v4" stroke="currentColor" strokeWidth="1.5" />
          </svg>
          <span className={styles.placeholderTitle}>{title}</span>
          <span className={styles.placeholderNote}>No poster yet</span>
        </div>
      )}
    </div>
  );
}
