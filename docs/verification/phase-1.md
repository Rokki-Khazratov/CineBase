# Phase 1 verification: Home → Search → Film prototype

Date: 26 October 2026. Branch `feat/cb-phase1-prototype`. Covers CB-101…CB-106 in
[TECHNICAL_SPEC.md](../TECHNICAL_SPEC.md) §7.

**Scope of this record.** All checks ran in desktop browsers driven by Playwright on one macOS machine, plus
manual review of screenshots. Narrow layouts were checked in **emulated browser viewports** (360, 390 and
768 px). Nothing here was tested on a physical phone, and no independent tester has used the prototype yet.

## Environment

| | |
| --- | --- |
| OS | macOS (Darwin 25.6) |
| Node / pnpm | 24.22.1 / 11.19.0 |
| Next.js / React | 16.4.3 / 19.3.0 |
| Browsers | Playwright 1.64.1: bundled Chromium and WebKit |
| Server | Production build (`pnpm build && pnpm start`) on port 3100 |

## Automated checks

| Check | Command | Result |
| --- | --- | --- |
| Lint | `pnpm lint` | Pass |
| Types | `pnpm typecheck` | Pass |
| Unit tests (catalog, fixtures, URL/query rules) | `pnpm test` | 65 / 65 pass |
| Production build | `pnpm build` | Pass. `/` and `/movies` static; 43 film pages prerendered |
| End-to-end | `pnpm test:e2e` | 177 / 177 pass (59 tests × 3 projects) |
| End-to-end, repeated | `playwright test --repeat-each=2` | 354 / 354 pass |

The e2e projects are Chromium 1440×900, WebKit 1440×900 and Chromium 360×800 with touch emulation.

### What the e2e suite covers

| Scenario | Tests |
| --- | --- |
| **U1** Home → film from a collection | Collections render; a card opens its film page |
| **U2** Find by title, alternate title, or title with year | Hero search shows title, year and director; `Сталкер` → Stalker; `Fabuleux destin` → Amélie; `Dune (2021)` ranks the 2021 film first; remakes of *Nosferatu* are told apart by year and director |
| **U3** Filters (partly in Phase 1 scope) | Genre, decade and sort are written to the URL, survive a reload and show in the controls; quick successive changes all apply |
| **U4** Film → back to results | *Back to results* restores the query, all 43 loaded cards and the scroll position (within 4 px); browser Back keeps the query and sort |
| Typing | Debounced URL update; slow typing (keys 254 ms apart) never loses letters |
| Paging | *Show more films* loads the next page and moves focus to its first card |
| States | Loading placeholders; no results with *Clear search*; error with *Try again* that recovers (`_fail=once`); missing artwork placeholder; announced film without an invented release date |
| 404 | `/movies/not-a-film` and an unknown UUID return HTTP 404 with a helpful page |
| Layout | No sideways scrolling on 9 pages at 360, 390, 768 and 1440 px, in all three projects |

## Bugs found by the checks and fixed

1. **Lost keystrokes during slow typing.** When a key arrived just after the debounced URL write, the URL sync
   copied the older value back into the box (`solaris` became `soaris`). It reproduced in Chromium and WebKit
   with keys about 250 ms apart. Fixed: the page never copies back a value it wrote itself. A regression test
   failed before the fix and passes 30 / 30 after it.
2. **Quick filter changes undoing each other.** A genre click followed at once by a sort change dropped the
   genre, because the second change was built from the not-yet-updated query. Fixed: every change starts from
   the current URL. A regression test failed in all three projects before the fix and passes after it.
3. **Genre chip name included the check mark** ("✓ Science Fiction"). The mark is now decorative; the
   selected state is announced through `aria-pressed`.
4. Earlier during development: horizontal overflow on Home from visually hidden card text escaping a
   scrolling row; unknown film IDs returning HTTP 200 (streamed page) instead of 404.

## Manual review

Screenshots in [screenshots/](screenshots/) were reviewed at 1440 px and at 390 px (2× pixel density).
The walkthrough recording is [walkthrough-desktop.mp4](walkthrough-desktop.mp4) (also as a
[GIF](walkthrough-desktop.gif)): Home → search *nosferatu* → film → *Back to results* → search *Сталкер* →
Drama filter and sort → clear filters → *Show more films* → scroll → film → *Back to results* at the same
place. No console errors were logged during the scripted walkthrough.

## Card density and search placement

[UI_DESIGN_DIRECTION.md](../UI_DESIGN_DIRECTION.md) asks to compare at least two card densities and search
placements and to choose one. This is the author's comparison from the screenshots and measurements below,
not a user study.

| | Comfortable | Compact |
| --- | --- | --- |
| Desktop 1440×900, cards at least partly in the first screen | 12 | 16 |
| Phone width 390×844, cards at least partly in the first screen | 2 | 6 |
| Readability at 390 px | Title, year and director on two lines | Three columns; director names wrap to three lines |

Screenshots: `density-desktop-*.png`, `density-mobile-390-*.png`.

**Decision:** *Comfortable* is the default because the year and director, which tell remakes apart, stay
readable at every width. *Compact* remains a per-browser toggle for scanning a long list.

**Search placement.** The prototype has a large page-level field (Home hero and the results toolbar) and a
compact header field (film and error pages). The results page uses the page-level field because it sits next
to the filters, so the current search and filters are visible together; the header field is hidden there to
avoid two search boxes. Film pages keep the header field so a new search does not need a trip back.

## Remaining gaps

- **No physical-phone check.** CB-106 asks for U1/U2/U4 on a phone; only emulated viewports were used.
- **No independent tester.** The Phase 1 acceptance criterion "passes the main path without the author's
  hints" has not been checked with another person.
- Firefox was not tested. No manual screen-reader pass (only accessible names and roles checked via tests).
- At 390 px the search and filter toolbar fills most of the first screen, so only the first row of results is
  visible before scrolling. A collapsible filter panel is a candidate improvement.
- The empty state has two buttons named "Clear search" (the field's × button and the text button).
- Fuzzy matching can add loose matches at the end of a list (for example *thing* also finds
  *Chungking Express*).
- Performance was not measured.
- The development switches `_latency=<ms>`, `_fail=1` and `_fail=once` also work in production builds. They
  are intended for this fixture prototype only.

## Reproducing

```sh
pnpm install
pnpm --filter web exec playwright install chromium webkit
pnpm lint && pnpm typecheck && pnpm test
pnpm test:e2e          # builds and starts the app on port 3100 unless it is already running
```
