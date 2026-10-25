#!/usr/bin/env node
// Generates the synthetic typographic posters in fixtures/art/posters from fixtures/movies.json.
// Output is deterministic: the same fixture data always produces byte-identical SVG files.
// Usage: node scripts/generate-posters.mjs [--check]
import { createHash } from "node:crypto";
import { mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const fixtures = join(root, "fixtures");
const outDir = join(fixtures, "art", "posters");
const check = process.argv.includes("--check");

const W = 400;
const H = 600;
const PAD = 30;

// Palettes: [background, field, motif, ink, muted ink]
const PALETTES = {
  ink: [["#151514", "#26241f", "#c8402f", "#f3efe6", "#a39d90"], ["#1d1b19", "#2f2b26", "#d9b64a", "#f5f1e8", "#a8a193"]],
  ice: [["#dfe8ec", "#c6d5dc", "#1f4e63", "#0f2530", "#4d6672"], ["#10242e", "#1b3a48", "#9fd0df", "#eef6f8", "#8aa8b3"]],
  sand: [["#e9dcc3", "#d8c29b", "#b2532a", "#2b1d12", "#6f5a44"], ["#c9853f", "#b06c2b", "#f2dfb6", "#24160b", "#5a3c20"]],
  neon: [["#17121f", "#2a1c3b", "#ff4f7b", "#f7eefc", "#a995b8"], ["#0e1b1a", "#16302d", "#3ee6c1", "#ecfbf7", "#86b1a8"]],
  dusk: [["#f2d7c9", "#e7b9a4", "#7a2e4a", "#2b1220", "#7a5160"], ["#3c2a4d", "#55396b", "#f2a65a", "#fbf1e6", "#c2a9c9"]],
  forest: [["#1f2b22", "#2d3f31", "#d8c36a", "#eef0e6", "#9fab97"], ["#d9dfcf", "#bfcbb0", "#2f5233", "#16231a", "#56664f"]],
  void: [["#f1efe9", "#e2ded4", "#1b1a18", "#1b1a18", "#6b675e"], ["#0b0b0d", "#1a1a1f", "#e8e4da", "#f4f1ea", "#8d8a82"]],
};
const STYLE_NAMES = Object.keys(PALETTES);

function hash(text) {
  return createHash("sha256").update(text).digest();
}

function esc(text) {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

// Rough advance widths for a bold grotesque, in em. Good enough to keep lines inside the frame.
function textWidth(text, size) {
  let em = 0;
  for (const ch of text) {
    if (/[　-鿿가-힯]/.test(ch)) em += 1;
    else if (/[MWmw@]/.test(ch)) em += 0.86;
    else if (/[A-Z0-9]/.test(ch)) em += 0.66;
    else if (/[il.,:;'!|ı]/.test(ch)) em += 0.28;
    else if (ch === " ") em += 0.27;
    else em += 0.56;
  }
  return em * size;
}

function wrap(text, size, maxWidth) {
  const words = text.split(/\s+/);
  const lines = [];
  let line = "";
  for (const word of words) {
    const next = line ? `${line} ${word}` : word;
    if (line && textWidth(next, size) > maxWidth) {
      lines.push(line);
      line = word;
    } else {
      line = next;
    }
  }
  if (line) lines.push(line);
  return lines;
}

function fitTitle(title) {
  const maxWidth = W - PAD * 2;
  for (let size = 64; size >= 22; size -= 2) {
    const lines = wrap(title, size, maxWidth);
    const fits = lines.every((l) => textWidth(l, size) <= maxWidth);
    if (fits && lines.length * size * 1.02 <= 240) return { size, lines };
  }
  return { size: 22, lines: wrap(title, 22, maxWidth) };
}

function motif(kind, h, [bg, field, accent]) {
  const n = (i) => h[i] / 255;
  const cx = Math.round(140 + n(4) * 120);
  const cy = Math.round(150 + n(5) * 80);
  switch (kind) {
    case 0: {
      const r = Math.round(70 + n(6) * 60);
      return `<circle cx="${cx}" cy="${cy}" r="${r}" fill="${accent}"/>` +
        `<rect x="0" y="${cy + Math.round(r * 0.35)}" width="${W}" height="${Math.round(r * 0.18)}" fill="${bg}"/>`;
    }
    case 1: {
      const rings = [];
      for (let i = 5; i >= 1; i--) {
        rings.push(`<circle cx="${cx}" cy="${cy}" r="${i * 26}" fill="none" stroke="${i % 2 ? accent : field}" stroke-width="13"/>`);
      }
      return rings.join("");
    }
    case 2: {
      const bands = [];
      const angle = -20 - Math.round(n(6) * 30);
      for (let i = 0; i < 6; i++) {
        bands.push(`<rect x="-200" y="${40 + i * 52}" width="800" height="${i % 2 ? 14 : 30}" fill="${i % 3 === 0 ? accent : field}"/>`);
      }
      return `<g transform="rotate(${angle} 200 200)">${bands.join("")}</g>`;
    }
    case 3: {
      const w = Math.round(150 + n(6) * 90);
      const x = Math.round((W - w) / 2);
      return `<path d="M${x} 360 V${210} a${w / 2} ${w / 2} 0 0 1 ${w} 0 V360 Z" fill="${accent}"/>` +
        `<path d="M${x + 28} 360 V${222} a${w / 2 - 28} ${w / 2 - 28} 0 0 1 ${w - 56} 0 V360 Z" fill="${field}"/>`;
    }
    case 4: {
      const dots = [];
      const step = 34;
      for (let y = 70; y <= 330; y += step) {
        for (let x = 46; x <= 354; x += step) {
          const d = Math.hypot(x - cx, y - cy);
          const r = Math.max(1.5, 13 - d / 18);
          dots.push(`<circle cx="${x}" cy="${y}" r="${r.toFixed(1)}" fill="${accent}"/>`);
        }
      }
      return dots.join("");
    }
    default: {
      const y = Math.round(150 + n(6) * 120);
      return `<rect x="${PAD}" y="70" width="${W - PAD * 2}" height="${y - 70}" fill="${field}"/>` +
        `<rect x="${PAD}" y="${y}" width="${Math.round((W - PAD * 2) * (0.35 + n(7) * 0.4))}" height="12" fill="${accent}"/>`;
    }
  }
}

function poster(movie, director, index) {
  const h = hash(`${movie.slug}:${movie.title}`);
  const style = STYLE_NAMES.includes(movie.poster.style) ? movie.poster.style : STYLE_NAMES[h[0] % STYLE_NAMES.length];
  const palette = PALETTES[style][h[1] % PALETTES[style].length];
  const [bg, field, , ink, muted] = palette;
  const kind = (index * 5 + h[2]) % 6;
  const { size, lines } = fitTitle(movie.title);
  const lineHeight = Math.round(size * 1.02);
  const titleBottom = H - 92;
  const titleTop = titleBottom - (lines.length - 1) * lineHeight;
  // Keep the motif clear of the meta line above and the title block below.
  const motifBottom = Math.round(titleTop - size * 0.85 - 16);
  const titleText = lines
    .map((l, i) => `<tspan x="${PAD}" y="${titleTop + i * lineHeight}">${esc(l)}</tspan>`)
    .join("");
  const original = movie.original_title && movie.original_title !== movie.title ? movie.original_title : null;
  const font = `'Helvetica Neue', Helvetica, Arial, 'Hiragino Sans', 'Noto Sans CJK JP', sans-serif`;
  const top = [movie.release_year, director].filter(Boolean).join("  ·  ").toUpperCase();

  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}">
<defs><clipPath id="motif"><rect x="0" y="58" width="${W}" height="${motifBottom - 58}"/></clipPath></defs>
<rect width="${W}" height="${H}" fill="${bg}"/>
<g clip-path="url(#motif)">${motif(kind, h, palette)}</g>
<g font-family="${font}" fill="${ink}">
<text x="${PAD}" y="${PAD + 12}" font-size="13" font-weight="600" letter-spacing="1.6" fill="${muted}">${esc(top)}</text>
<text font-size="${size}" font-weight="800" letter-spacing="-0.5">${titleText}</text>
${original ? `<text x="${PAD}" y="${H - 58}" font-size="16" font-weight="500" fill="${muted}">${esc(original)}</text>` : ""}
<rect x="${PAD}" y="${H - 40}" width="${W - PAD * 2}" height="1" fill="${muted}" opacity="0.6"/>
<text x="${PAD}" y="${H - 20}" font-size="10" font-weight="600" letter-spacing="1.4" fill="${muted}">CINEBASE FIXTURE · ILLUSTRATIVE POSTER</text>
</g>
</svg>
`;
}

const movies = JSON.parse(readFileSync(join(fixtures, "movies.json"), "utf8"));
const people = new Map(JSON.parse(readFileSync(join(fixtures, "people.json"), "utf8")).map((p) => [p.slug, p]));
const expected = new Map();
for (const [index, movie] of movies.entries()) {
  if (!movie.poster) continue;
  const directors = movie.credits
    .filter((c) => c.department === "Directing" && c.job === "Director")
    .map((c) => people.get(c.person).name);
  expected.set(movie.poster.file.replace(/^posters\//, ""), poster(movie, directors.join(" & "), index));
}

if (check) {
  let stale = 0;
  for (const [file, svg] of expected) {
    const path = join(outDir, file);
    if (!existsSync(path) || readFileSync(path, "utf8") !== svg) {
      console.error(`stale or missing: ${file}`);
      stale++;
    }
  }
  if (stale) process.exit(1);
  console.log(`${expected.size} posters up to date`);
} else {
  mkdirSync(outDir, { recursive: true });
  for (const file of readdirSync(outDir)) if (!expected.has(file)) rmSync(join(outDir, file));
  for (const [file, svg] of expected) writeFileSync(join(outDir, file), svg);
  console.log(`wrote ${expected.size} posters to ${outDir}`);
}
