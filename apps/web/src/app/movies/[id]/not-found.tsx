import Link from "next/link";
import { StatePanel } from "@/components/states/StatePanel";
import buttons from "@/components/ui/Button.module.css";

export default function FilmNotFound() {
  return (
    <StatePanel
      headingLevel="h1"
      title="This film isn’t in the catalog"
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
      <p>The link may be mistyped, or the film may have been removed. Search by title to find it.</p>
    </StatePanel>
  );
}
