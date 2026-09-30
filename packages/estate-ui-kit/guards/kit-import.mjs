#!/usr/bin/env node
// Kit-import guard (crew#694 CP4): a front end that does not import the kit's tokens is refused.
// Reads consumers.json beside this file. Each consumer names its root and the stylesheet that must
// import "@estate/ui-kit". A consumer with `migrate_by` is legacy: a warning until that date, a
// refusal after it. A consumer whose root is not in this checkout is skipped and said so.
// Any apps/*/ directory in the repo is a consumer by definition (that is what ui.scaffold creates).
import { readFileSync, existsSync, readdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const repo = join(here, '..', '..', '..');
const list = JSON.parse(readFileSync(join(here, '..', 'consumers.json'), 'utf8'));
const appsDir = join(repo, 'apps');
if (existsSync(appsDir)) for (const d of readdirSync(appsDir)) {
  if (existsSync(join(appsDir, d, 'package.json')) && !list.some((c) => c.root === `apps/${d}`)) list.push({ root: `apps/${d}`, css: 'src/styles/global.css', note: 'auto-discovered app' });
}
const today = new Date().toISOString().slice(0, 10);
let fail = 0;
for (const c of list) {
  const root = c.root.startsWith('~') ? c.root.replace('~', process.env.HOME ?? '') : join(repo, c.root);
  if (!existsSync(root)) { console.log(`skip   ${c.root}: not in this checkout`); continue; }
  const css = join(root, c.css);
  const ok = existsSync(css) && /@estate\/ui-kit/.test(readFileSync(css, 'utf8'));
  if (ok) { console.log(`ok     ${c.root}: ${c.css} imports @estate/ui-kit`); continue; }
  if (c.migrate_by && c.migrate_by >= today) { console.log(`warn   ${c.root}: no kit import yet; legacy until ${c.migrate_by}`); continue; }
  console.error(`REFUSE ${c.root}: ${c.css} does not import @estate/ui-kit${c.migrate_by ? ` (deadline ${c.migrate_by} passed)` : ''}`);
  fail = 1;
}
process.exit(fail);
