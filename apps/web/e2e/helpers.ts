import { expect, type Page } from "@playwright/test";

/**
 * Next.js keeps routes you navigate away from mounted but hidden, so the same element can exist twice in
 * the DOM. Every query here is limited to what is actually on screen.
 */
export const cards = (page: Page) => page.locator("article:visible");
export const cardTitles = (page: Page) => page.locator("article:visible h2");
export const resultCount = (page: Page) => page.locator("[aria-live=polite]:visible").first();
export const resultsSearch = (page: Page) => page.locator("#results-search:visible");

export const FILMS = {
  nosferatu1922: "175733e5-fa4e-53e5-b141-a19b99ed1415",
  stalker: "809d0284-dba9-5518-845f-89c1390ef6cd",
  dune2021: "c730facf-2923-59ec-8297-f3166c0eb5a8",
  duneThree: "a17dec17-00f9-5cd0-b1bc-2a1d50c1b05f",
} as const;

/** Opens a "Browse by" menu (Genre, Hide) and returns it. */
export async function openMenu(page: Page, label: "Genre" | "Hide") {
  const menu = page.locator("details:visible", { has: page.locator("summary", { hasText: label }) });
  if (!(await menu.evaluate((d: HTMLDetailsElement) => d.open))) await menu.locator("summary").click();
  return menu;
}

export const menuSummary = (page: Page, label: "Genre" | "Hide") => page.locator("summary:visible", { hasText: label });

export async function waitForResults(page: Page) {
  await expect(cardTitles(page).first()).toBeVisible();
}

/** Horizontal overflow of the document in CSS pixels; 0 means no sideways scrolling. */
export function horizontalOverflow(page: Page) {
  return page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
}
