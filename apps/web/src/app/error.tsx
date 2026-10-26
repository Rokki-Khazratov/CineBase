"use client";

import { StatePanel } from "@/components/states/StatePanel";
import buttons from "@/components/ui/Button.module.css";

export default function AppError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <StatePanel
      tone="error"
      headingLevel="h1"
      title="Something went wrong"
      actions={
        <button type="button" className={`${buttons.button} ${buttons.primary}`} onClick={reset}>
          Try again
        </button>
      }
    >
      <p>This page couldn’t be shown. Trying again usually fixes it.</p>
    </StatePanel>
  );
}
