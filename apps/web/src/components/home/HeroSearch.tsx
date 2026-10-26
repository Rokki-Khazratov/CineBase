"use client";

import Form from "next/form";
import { useState } from "react";
import { SearchField } from "@/components/search/SearchField";
import buttons from "@/components/ui/Button.module.css";
import styles from "./Home.module.css";

/** Home search: a plain GET form to /movies, so it works before JavaScript loads and navigates client-side after. */
export function HeroSearch() {
  const [value, setValue] = useState("");
  return (
    <Form action="/movies" role="search" className={styles.heroForm}>
      <SearchField id="home-search" value={value} onChange={setValue} onClear={() => setValue("")} size="large" />
      <button type="submit" className={`${buttons.button} ${buttons.primary} ${styles.heroSubmit}`}>
        Search
      </button>
    </Form>
  );
}
