import { describe, expect, it } from "vitest";
import { bestSimilarity, normalizeText, parseTitleYear, similarity, trigrams } from "./normalize";

describe("normalizeText", () => {
  it.each([
    ["Amélie", "amelie"],
    ["  SUSPIRIA  ", "suspiria"],
    ["Ocean's 11", "oceans 11"],
    ["Ocean’s Eleven", "oceans eleven"],
    ["Dr. Strangelove or: How I Learned", "dr strangelove or how i learned"],
    ["Paris, Texas", "paris texas"],
    ["Låt den rätte komma in", "lat den ratte komma in"],
    ["Tōkyō monogatari", "tokyo monogatari"],
    ["Stanisław Lem", "stanislaw lem"],
    ["Straße", "strasse"],
    ["8½", "8 1/2"],
    ["8 1/2", "8 1/2"],
    ["2001: A Space Odyssey", "2001 a space odyssey"],
    ["Солярис", "солярис"],
    ["七人の侍", "七人の侍"],
  ])("%s → %s", (input, expected) => {
    expect(normalizeText(input)).toBe(expected);
  });

  it("returns an empty key for punctuation only", () => {
    expect(normalizeText(" ?!… ")).toBe("");
  });
});

describe("parseTitleYear", () => {
  it("extracts a trailing (YYYY)", () => {
    expect(parseTitleYear("Suspiria (2018)")).toEqual({ text: "Suspiria", year: 2018 });
    expect(parseTitleYear("  The Thing(1982) ")).toEqual({ text: "The Thing", year: 1982 });
  });

  it("leaves other numbers in the title", () => {
    expect(parseTitleYear("2001: A Space Odyssey")).toEqual({ text: "2001: A Space Odyssey", year: null });
    expect(parseTitleYear("12 Angry Men")).toEqual({ text: "12 Angry Men", year: null });
    expect(parseTitleYear("Ocean's 11")).toEqual({ text: "Ocean's 11", year: null });
    expect(parseTitleYear("(1984)")).toEqual({ text: "(1984)", year: null });
  });
});

describe("similarity", () => {
  it("scores identical strings as 1 and unrelated strings near 0", () => {
    expect(similarity(trigrams("stalker"), trigrams("stalker"))).toBe(1);
    expect(similarity(trigrams("stalker"), trigrams("parasite"))).toBeLessThan(0.1);
  });

  it("tolerates a typo above the 0.3 threshold", () => {
    expect(similarity(trigrams("suspira"), trigrams("suspiria"))).toBeGreaterThan(0.3);
  });

  it("matches a misspelled word inside a longer title", () => {
    const q = "labyrinht";
    expect(bestSimilarity(q, trigrams(q), "pans labyrinth")).toBeGreaterThan(0.3);
  });
});
