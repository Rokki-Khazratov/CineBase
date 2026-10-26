import { expect, test } from "@playwright/test";
import { FILMS, horizontalOverflow } from "./helpers";

const PAGES = {
  home: "/",
  results: "/movies?q=nosferatu",
  browse: "/movies",
  filters: "/movies?genre=drama&year_from=2000&year_to=2009&sort=title_asc",
  empty: "/movies?q=zzzzqqq",
  error: "/movies?q=dune&_fail=1",
  film: `/movies/${FILMS.nosferatu1922}`,
  "film without runtime": `/movies/${FILMS.stalker}`,
  "not found": "/movies/not-a-film",
};

for (const width of [360, 390, 768, 1440]) {
  test.describe(`at ${width}px`, () => {
    test.use({ viewport: { width, height: width < 800 ? 800 : 900 } });
    for (const [name, path] of Object.entries(PAGES)) {
      test(`${name} has no sideways scrolling`, async ({ page }) => {
        await page.goto(path);
        await page.waitForLoadState("networkidle");
        expect(await horizontalOverflow(page)).toBe(0);
      });
    }
  });
}
