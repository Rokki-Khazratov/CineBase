import Link from "next/link";
import { StatePanel } from "@/components/states/StatePanel";
import buttons from "@/components/ui/Button.module.css";

/** Also shown for unknown film IDs (see src/proxy.ts), so the copy covers both cases. */
export default function NotFound() {
  return (
    <StatePanel
      headingLevel="h1"
      title="We couldn’t find that page or film"
      actions={
        <>
          <Link href="/movies" className={`${buttons.button} ${buttons.primary}`}>
            Search films
          </Link>
          <Link href="/" className={buttons.button}>
            Go to home
          </Link>
        </>
      }
    >
      <p>The link may be mistyped, or the film may no longer be in the catalog. Searching by title usually finds it.</p>
    </StatePanel>
  );
}
