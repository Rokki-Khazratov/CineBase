import type { MovieSummary, PersonRef } from "@/catalog";

export function directorNames(directors: PersonRef[]): string {
  if (directors.length === 0) return "Director unknown";
  if (directors.length === 1) return directors[0].name;
  return `${directors.slice(0, -1).map((d) => d.name).join(", ")} & ${directors.at(-1)!.name}`;
}

export function yearLabel(movie: Pick<MovieSummary, "year">): string {
  return movie.year === null ? "Year unknown" : String(movie.year);
}

export function runtimeLabel(minutes: number | null): string | null {
  if (minutes === null) return null;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return h === 0 ? `${m} min` : m === 0 ? `${h} h` : `${h} h ${m} min`;
}

export function formatDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" }).format(
    new Date(Date.UTC(y, m - 1, d)),
  );
}

const languageNames = new Intl.DisplayNames(["en"], { type: "language" });
const regionNames = new Intl.DisplayNames(["en"], { type: "region" });

export function languageName(code: string | null): string | null {
  if (!code) return null;
  try {
    return languageNames.of(code) ?? code;
  } catch {
    return code;
  }
}

/** Historical countries are not in CLDR region data. */
const HISTORICAL_REGIONS: Record<string, string> = { SU: "Soviet Union" };

export function countryName(code: string | null): string | null {
  if (!code) return null;
  if (HISTORICAL_REGIONS[code]) return HISTORICAL_REGIONS[code];
  try {
    return regionNames.of(code) ?? code;
  } catch {
    return code;
  }
}

/** "ru-Latn" → "Russian, romanized"; "en" → "English". */
export function localeLabel(locale: string | null): string | null {
  if (!locale) return null;
  const [base, script] = locale.split("-");
  const language = languageName(base);
  return script === "Latn" ? `${language}, romanized` : language;
}

export function releaseLabel(release: { status: "released" | "announced"; date: string | null; country: string | null }, year: number | null): string {
  const country = countryName(release.country);
  const where = country ? ` (${country})` : "";
  if (release.status === "announced") {
    if (release.date) return `Announced for ${formatDate(release.date)}${where}`;
    return year ? `Announced for ${year}` : "Announced, date not set";
  }
  if (release.date) return `${formatDate(release.date)}${where}`;
  return year ? `${year} (${country ? `${country}, ` : ""}exact date unknown)` : "Unknown";
}
