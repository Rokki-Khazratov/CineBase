import { expect, test } from "@playwright/test";
import { cards, resultCount, waitForResults } from "./helpers";

test("home shows the search, example searches and collections", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: "Find the film you mean." })).toBeVisible();
  await expect(page.locator("#home-search")).toBeVisible();
  await expect(page.locator("section[aria-labelledby] ul[aria-label]").first()).toBeVisible();
  await expect(page.getByRole("heading", { name: /genre/i })).toBeVisible();
});

test("hero search opens results with title, year and director", async ({ page }) => {
  await page.goto("/");
  await page.locator("#home-search").fill("nosferatu");
  await page.locator("#home-search").press("Enter");
  await expect(page).toHaveURL(/\/movies\?q=nosferatu$/);
  await waitForResults(page);
  await expect(resultCount(page)).toHaveText("3 films found for “nosferatu”");
  // Exact title matches come first, newest first, told apart by year and director; then the longer title.
  await expect(cards(page).nth(0)).toContainText(/^Nosferatu2024.*Robert Eggers/s);
  await expect(cards(page).nth(1)).toContainText(/^Nosferatu1922.*F\. W\. Murnau/s);
  await expect(cards(page).nth(2)).toContainText(/^Nosferatu the Vampyre1979.*Werner Herzog/s);
});

test("an example search link runs that search", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Сталкер" }).click();
  await waitForResults(page);
  await expect(cards(page).first()).toContainText("Stalker");
});

test("a film opens from a home collection (U1)", async ({ page }) => {
  await page.goto("/");
  const firstCard = page.locator("section[aria-labelledby] ul[aria-label] article").first();
  const title = await firstCard.locator("h2, h3").first().innerText();
  await firstCard.getByRole("link").click();
  await expect(page).toHaveURL(/\/movies\/[0-9a-f-]{36}$/);
  await expect(page.getByRole("heading", { level: 1, name: title })).toBeVisible();
});
