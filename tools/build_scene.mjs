/* Bundle the state-space scene into one committed file.
 *
 *   node tools/build_scene.mjs
 *
 * Output: assets/atlas.js — tree-shaken three + the scene, committed to the
 * repo. Vercel keeps serving static files and "push to main" is unchanged;
 * no bundler runs at deploy time. Same contract as tools/build_writing.py:
 * the generator runs locally, its output is the artifact.
 *
 * three lives in hpccc's node_modules (three@0.185). We resolve against it
 * rather than adding a package.json here, so this repo stays dependency-free.
 */
import { execFileSync } from 'node:child_process';
import { gzipSync } from 'node:zlib';
import { readFileSync, writeFileSync, existsSync, symlinkSync, unlinkSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const HPCCC = '/Users/lauriszvirbulis/Downloads/hpccc/prototypes/calder-brief';
const ESBUILD = join(HPCCC, 'node_modules/.bin/esbuild');
const LINK = join(ROOT, 'tools', 'node_modules');
const ENTRY = join(ROOT, 'tools', 'scene', 'atlas.mjs');
const OUT = join(ROOT, 'assets', 'atlas.js');

// The ceiling we agreed. three's renderer is effectively monolithic, so this
// lands ~130KB however little of the API the scene touches. If a future
// change pushes it past this, that's a decision to take deliberately.
const GATE = 140_000;

for (const p of [ESBUILD, join(HPCCC, 'node_modules/three')]) {
  if (!existsSync(p)) {
    console.error(`missing: ${p}\nThis build needs hpccc's node_modules for esbuild + three.`);
    process.exit(1);
  }
}

if (!existsSync(LINK)) symlinkSync(join(HPCCC, 'node_modules'), LINK, 'dir');
try {
  execFileSync(ESBUILD, [
    ENTRY, '--bundle', '--format=iife', '--minify', '--tree-shaking=true',
    '--target=es2020', `--outfile=${OUT}`, '--log-level=warning',
  ], { stdio: 'inherit', cwd: join(ROOT, 'tools') });
} finally {
  try { unlinkSync(LINK); } catch {}
}

// Shader chunks in three preserve spaces before line breaks inside template
// literals. They are semantically inert, but keeping them makes the committed
// artifact fail `git diff --check`. Normalize the bundle after every build so
// the generated file is deterministic and repository-clean.
const normalized = readFileSync(OUT, 'utf8')
  .replace(/[\t ]+$/gm, '')
  .replace(/^ +\t/gm, '\t');
writeFileSync(OUT, normalized);

const raw = readFileSync(OUT);
const gz = gzipSync(raw).length;
const site = gzipSync(readFileSync(join(ROOT, 'index.html'))).length;
console.log(`\nassets/atlas.js  raw=${raw.length}  gzip=${gz} (${(gz / 1024).toFixed(1)}KB)`);
console.log(`the site itself   gzip=${site} — the scene is ${(gz / site).toFixed(1)}x the page it sits on`);
if (gz > GATE) {
  console.error(`\nHALT: ${gz} > ${GATE} gate. Not shipping this.`);
  process.exit(1);
}
console.log(`gate ${GATE}: PASS`);
