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
import { execFileSync } from 'node:child_process';
import { migrationAdmission } from './consumer-migration.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const kitRoot = join(here, '..');
const repo = join(here, '..', '..', '..');
const list = JSON.parse(readFileSync(join(kitRoot, 'consumers.json'), 'utf8'));
const appsDir = join(repo, 'apps');
if (existsSync(appsDir)) for (const d of readdirSync(appsDir)) {
  if (existsSync(join(appsDir, d, 'package.json')) && !list.some((c) => c.root === `apps/${d}`)) list.push({ root: `apps/${d}`, css: 'src/styles/global.css', note: 'auto-discovered app' });
}
const today = new Date().toISOString().slice(0, 10);
// A legacy migration deadline must not turn unrelated emergency fixes red.
// Resolve the actual candidate-vs-main diff, rather than treating time alone
// as proof a stylesheet regressed. Missing Git evidence is fail-closed.
function stylesheetChanged(path) {
  try {
    const base = execFileSync('git', ['merge-base', 'HEAD', 'origin/main'], { cwd: repo, encoding: 'utf8' }).trim();
    if (!base) return null;
    const committed = execFileSync('git', ['diff', '--name-only', base, 'HEAD', '--', path], { cwd: repo, encoding: 'utf8' }).trim();
    const working = execFileSync('git', ['status', '--porcelain', '--', path], { cwd: repo, encoding: 'utf8' }).trim();
    return Boolean(committed || working);
  } catch {
    return null;
  }
}
let fail = 0;
for (const c of list) {
  const root = c.root.startsWith('~') ? c.root.replace('~', process.env.HOME ?? '') : join(repo, c.root);
  if (!existsSync(root)) { console.log(`skip   ${c.root}: not in this checkout`); continue; }
  const css = join(root, c.css);
  const text = existsSync(css) ? readFileSync(css, 'utf8') : '';
  const ok = /@estate\/ui-kit/.test(text);
  if (!ok) {
    // CSS disappearance always fails: it is not harmless unchanged baseline debt.
    if (!existsSync(css)) {
      console.error(`REFUSE ${c.root}: required stylesheet ${c.css} missing`);
      fail = 1;
      continue;
    }
    const changed = c.migrate_by && c.migrate_by < today
      ? stylesheetChanged(c.root + '/' + c.css) : null;
    const admission = migrationAdmission({
      hasImport: false, migrationDeadline: c.migrate_by, today, stylesheetChanged: changed,
    });
    if (admission.accept) {
      console.warn(`warn   ${c.root}: ${admission.reason}; migration still owed, not declared complete`);
      continue;
    }
    console.error(`REFUSE ${c.root}: ${admission.reason}; ${c.css} must import @estate/ui-kit`);
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
