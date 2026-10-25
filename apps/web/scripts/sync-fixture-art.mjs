#!/usr/bin/env node
// Copies committed fixture art (fixtures/art) into public/fixture-art so Next.js can serve it.
// public/fixture-art is gitignored; fixtures/art is the single source of truth.
import { cpSync, rmSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const web = join(dirname(fileURLToPath(import.meta.url)), "..");
const source = join(web, "..", "..", "fixtures", "art");
const target = join(web, "public", "fixture-art");

rmSync(target, { recursive: true, force: true });
cpSync(source, target, { recursive: true });
console.log("fixture art synced to public/fixture-art");
