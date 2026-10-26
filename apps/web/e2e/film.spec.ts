import { expect, test } from "@playwright/test";
import { cards, cardTitles, FILMS, resultsSearch, waitForResults } from "./helpers";

test("film page shows details, credits and other versions", async ({ page }) => {
  await page.goto(`/movies/${FILMS.nosferatu1922}`);
  await expect(page.getByRole("heading", { level: 1, name: "Nosferatu" })).toBeVisible();
  await expect(page.getByText("Directed by F. W. Murnau", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Synopsis" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Other films with this title" })).toBeVisible();
  await expect(page.locator("section[aria-labelledby=others-heading] article")).toHaveCount(2);
});

test("an announced film says so instead of inventing a release", async ({ page }) => {
  await page.goto(`/movies/${FILMS.duneThree}`);
  await expect(page.getByRole("heading", { level: 1, name: "Dune: Part Three" })).toBeVisible();
  await expect(page.getByText(/Announced/).first()).toBeVisible();
});

test("an unknown film ID returns a real 404 page", async ({ page }) => {
  const response = await page.goto("/movies/not-a-film");
  expect(response?.status()).toBe(404);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("We couldn’t find that page or film");
  const missing = await page.goto("/movies/00000000-0000-5000-8000-000000000000");
  expect(missing?.status()).toBe(404);
});

test("Back to results restores the query, loaded cards and scroll position", async ({ page }) => {
  await page.goto("/movies");
  await waitForResults(page);
  await page.getByRole("button", { name: "Show more films" }).click();
  await expect(cards(page)).toHaveCount(43);

  const target = cards(page).nth(30);
  await target.scrollIntoViewIfNeeded();
  const title = await cardTitles(page).nth(30).innerText();
  const scrollBefore = await page.evaluate(() => scrollY);
  expect(scrollBefore).toBeGreaterThan(500);

  await target.getByRole("link").click();
  await expect(page).toHaveURL(/\/movies\/[0-9a-f-]{36}$/);
  await expect(page.getByRole("heading", { level: 1, name: title })).toBeVisible();

  await page.getByRole("link", { name: "Back to results" }).click();
  await expect(page).toHaveURL(/\/movies$/);
  await expect(cards(page)).toHaveCount(43);
  await expect(cardTitles(page).nth(30)).toHaveText(title);
  await expect.poll(() => page.evaluate(() => scrollY)).toBeGreaterThan(scrollBefore - 4);
  expect(Math.abs((await page.evaluate(() => scrollY)) - scrollBefore)).toBeLessThanOrEqual(4);
});

test("browser Back from a film keeps the search and filters", async ({ page }) => {
  await page.goto("/movies?q=nosferatu&sort=release_desc");
  await waitForResults(page);
  await cards(page).nth(1).getByRole("link").click();
  await expect(page).toHaveURL(/\/movies\/[0-9a-f-]{36}$/);
  await page.goBack();
  await expect(page).toHaveURL(/q=nosferatu&sort=release_desc/);
  await expect(resultsSearch(page)).toHaveValue("nosferatu");
  await expect(cards(page)).toHaveCount(3);
});

test("a film opened directly offers a way into the catalog", async ({ page }) => {
  await page.goto(`/movies/${FILMS.stalker}`);
  await expect(page.getByRole("link", { name: "Browse all films" })).toBeVisible();
});

test("the header search works from a film page", async ({ page }) => {
  await page.goto(`/movies/${FILMS.stalker}`);
  await page.locator("#header-search").fill("thing");
  await page.locator("#header-search").press("Enter");
  await expect(page).toHaveURL(/q=thing/);
  await waitForResults(page);
  await expect(resultsSearch(page)).toHaveValue("thing");
});
