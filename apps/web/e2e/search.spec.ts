import { expect, test } from "@playwright/test";
import { cards, cardTitles, menuSummary, openMenu, resultCount, resultsSearch, waitForResults } from "./helpers";

test("typing searches after a short pause and updates the URL", async ({ page }) => {
  await page.goto("/movies");
  await waitForResults(page);
  await resultsSearch(page).pressSequentially("solaris", { delay: 40 });
  await expect(page).toHaveURL(/q=solaris/);
  await expect(cardTitles(page)).toHaveText(["Solaris", "Solaris"]);
});

test("slow typing never loses letters to the debounced URL update", async ({ page }) => {
  await page.goto("/movies");
  await waitForResults(page);
  // Each key lands just after the previous debounced URL write (250 ms), while that write is being applied.
  await resultsSearch(page).pressSequentially("solaris", { delay: 254 });
  await expect(page).toHaveURL(/q=solaris$/);
  await expect(resultsSearch(page)).toHaveValue("solaris");
});

test("alternate and original titles find the film", async ({ page }) => {
  await page.goto("/movies?q=" + encodeURIComponent("Сталкер"));
  await waitForResults(page);
  await expect(cardTitles(page).first()).toHaveText("Stalker");

  await page.goto("/movies?q=" + encodeURIComponent("Fabuleux destin"));
  await waitForResults(page);
  await expect(cards(page).first()).toContainText("Amélie");
});

test("a year in the search ranks that release first", async ({ page }) => {
  await page.goto("/movies?q=" + encodeURIComponent("Dune (2021)"));
  await waitForResults(page);
  await expect(cards(page).first()).toContainText("2021");
});

test("filters and sort are written to the URL and survive a reload", async ({ page }) => {
  await page.goto("/movies?q=dune");
  await waitForResults(page);

  await (await openMenu(page, "Genre")).getByRole("checkbox", { name: "Science Fiction" }).check();
  await expect(page).toHaveURL(/genre=science-fiction/);
  await page.keyboard.press("Escape");
  await page.getByLabel("Sort by").selectOption("title_asc");
  await expect(page).toHaveURL(/sort=title_asc/);
  await expect(cardTitles(page).first()).toHaveText("Dune");

  await page.reload();
  await waitForResults(page);
  await expect(resultsSearch(page)).toHaveValue("dune");
  await expect(page.getByLabel("Sort by")).toHaveValue("title_asc");
  await expect(menuSummary(page, "Genre")).toContainText("Science Fiction");
  await expect((await openMenu(page, "Genre")).getByRole("checkbox", { name: "Science Fiction" })).toBeChecked();
});

test("quick successive filter changes all apply", async ({ page }) => {
  await page.goto("/movies");
  await waitForResults(page);
  await openMenu(page, "Genre");
  // Three changes in one task, before React has re-rendered from the first URL update.
  await page.evaluate(() => {
    const boxes = [...document.querySelectorAll<HTMLInputElement>("input[type=checkbox]")].filter((b) => b.checkVisibility());
    boxes.find((b) => b.parentElement?.textContent === "Drama")!.click();
    boxes.find((b) => b.parentElement?.textContent === "Horror")!.click();
    const sort = [...document.querySelectorAll("label")].find((l) => l.textContent?.startsWith("Sort by") && l.checkVisibility())!.querySelector("select")!;
    sort.value = "title_asc";
    sort.dispatchEvent(new Event("change", { bubbles: true }));
  });
  await expect(page).toHaveURL(/genre=drama&genre=horror&sort=title_asc$/);
  await expect(menuSummary(page, "Genre")).toContainText("Drama +1");
});

test("Hide removes unreleased films and is kept in the URL", async ({ page }) => {
  await page.goto("/movies?genre=horror");
  await waitForResults(page);
  await (await openMenu(page, "Hide")).getByRole("checkbox", { name: "Unreleased films" }).check();
  await expect(page).toHaveURL(/exclude=unreleased/);
  await expect(menuSummary(page, "Hide")).toContainText("1 selected");
  await expect(resultCount(page)).toHaveText(/^There (are|is) \d+ films? matching your filters$/);
  await page.getByRole("button", { name: "Clear filters" }).click();
  await expect(page).toHaveURL(/\/movies$/);
});

test("a decade filter from the URL is reflected in the controls", async ({ page }) => {
  await page.goto("/movies?genre=horror&year_from=1970&year_to=1979");
  await waitForResults(page);
  await expect(page.getByLabel("Decade")).toHaveValue("1970");
  for (const text of await cards(page).allInnerTexts()) expect(text).toMatch(/197\d/);
});

test("Show more films loads the next page and moves focus to it", async ({ page }) => {
  await page.goto("/movies");
  await waitForResults(page);
  await expect(resultCount(page)).toHaveText("There are 43 films");
  await expect(cards(page)).toHaveCount(24);
  await page.getByRole("button", { name: "Show more films" }).click();
  await expect(cards(page)).toHaveCount(43);
  await expect(resultCount(page)).toHaveText("There are 43 films");
  await expect(cards(page).nth(24).getByRole("link")).toBeFocused();
});

test("no results explains why and offers a way out", async ({ page }) => {
  await page.goto("/movies?q=zzzzqqq&genre=horror");
  await expect(page.getByRole("heading", { name: "No films match “zzzzqqq”" })).toBeVisible();
  await page.getByRole("button", { name: "Clear search" }).and(page.getByText("Clear search")).click();
  await expect(page).not.toHaveURL(/q=/);
  await waitForResults(page);
  await expect(menuSummary(page, "Genre")).toContainText("Horror");
});

test("a failed request shows an error, and Try again recovers", async ({ page }) => {
  await page.goto("/movies?q=dune&_fail=once");
  await expect(page.getByRole("heading", { name: "Films couldn’t be loaded" })).toBeVisible();
  await expect(page.getByText("Error 503 · catalog_unavailable")).toBeVisible();
  await page.getByRole("button", { name: "Try again" }).click();
  await waitForResults(page);
  await expect(cards(page).first()).toContainText("Dune");
});

test("loading shows placeholders while results are on the way", async ({ page }) => {
  await page.goto("/movies?q=dune&_latency=5000");
  await expect(page.locator("[data-loading-placeholder]:visible").first()).toBeVisible();
  await expect(cardTitles(page).first()).toBeVisible({ timeout: 10_000 });
});
