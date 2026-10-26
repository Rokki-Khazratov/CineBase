import type { Metadata, Viewport } from "next";
import { SiteFooter } from "@/components/site/SiteFooter";
import { SiteHeader } from "@/components/site/SiteHeader";
import "./globals.css";
import styles from "./layout.module.css";

export const metadata: Metadata = {
  title: {
    default: "CineBase",
    template: "%s · CineBase",
  },
  description: "Find a film and the facts about it: titles, years, directors, cast and runtime.",
};

export const viewport: Viewport = {
  themeColor: "#f7f6f3",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>
        <a href="#main" className={styles.skip}>
          Skip to content
        </a>
        <SiteHeader />
        <main id="main" className={styles.main} tabIndex={-1}>
          {children}
        </main>
        <SiteFooter />
      </body>
    </html>
  );
}
