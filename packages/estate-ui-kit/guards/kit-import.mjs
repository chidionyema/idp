#!/usr/bin/env node
// Kit-import guard (crew#694 CP4): a front end that does not import the kit's tokens is refused.
// Reads consumers.json beside this file. Each consumer names its root and the stylesheet that must
// import "@estate/ui-kit". A consumer with `migrate_by` is legacy: a warning until that date, a
// refusal after it. A consumer whose root is not in this checkout is skipped and said so.
// Any apps/*/ directory in the repo is a consumer by definition (that is what ui.scaffold creates).
//
// Two refusals, both about the import being real:
//   - the stylesheet imports the kit but the consumer's package.json does not declare the
//     dependency, so the import cannot resolve (an import that cannot resolve is worse than none);
//   - the consumer names a brand that the kit does not carry, so the brand CSS cannot resolve.
import { readFileSync, existsSync, readdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const kitRoot = join(here, '..');
const repo = join(here, '..', '..', '..');
const list = JSON.parse(readFileSync(join(kitRoot, 'consumers.json'), 'utf8'));
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
  const text = existsSync(css) ? readFileSync(css, 'utf8') : '';
  const ok = /@estate\/ui-kit/.test(text);
  if (!ok) {
    if (c.migrate_by && c.migrate_by >= today) { console.log(`warn   ${c.root}: no kit import yet; legacy until ${c.migrate_by}`); continue; }
    console.error(`REFUSE ${c.root}: ${c.css} does not import @estate/ui-kit${c.migrate_by ? ` (deadline ${c.migrate_by} passed)` : ''}`);
    fail = 1;
    continue;
  }
  // The import must resolve: the dependency has to be declared, and the brand has to exist.
  const pkgPath = join(root, 'package.json');
  if (existsSync(pkgPath)) {
    const pkg = JSON.parse(readFileSync(pkgPath, 'utf8'));
    const deps = { ...(pkg.dependencies ?? {}), ...(pkg.devDependencies ?? {}) };
    if (!deps['@estate/ui-kit']) {
      console.error(`REFUSE ${c.root}: ${c.css} imports @estate/ui-kit but package.json does not declare the dependency`);
      fail = 1;
      continue;
    }
  }
  if (c.brand && !existsSync(join(kitRoot, 'brands', `${c.brand}.json`))) {
    console.error(`REFUSE ${c.root}: brand "${c.brand}" is not in packages/estate-ui-kit/brands/`);
    fail = 1;
    continue;
  }
  console.log(`ok     ${c.root}: ${c.css} imports @estate/ui-kit${c.brand ? ` + brand ${c.brand}` : ''}`);
}
process.exit(fail);
