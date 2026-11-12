import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, mkdirSync, mkdtempSync, copyFileSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const script = join(root, 'scripts', 'merdian-public-release-gate.mjs');
const sources = [
  'app/page.tsx', 'app/layout.tsx', 'app/merian.css', 'app/globals.css',
  'app/manifest.ts', 'app/opengraph-image.tsx',
  'components/Logo.tsx', 'components/Nav.tsx', 'components/Footer.tsx',
  'content/site.ts', 'app/products/page.tsx', 'app/research/page.tsx',
  'app/consulting/page.tsx', 'app/contact/page.tsx', 'app/contact/layout.tsx',
  'app/case-studies/page.tsx', 'app/tooling/page.tsx', 'app/writing/page.tsx',
  'app/products/chronos/page.tsx',
  'app/writing/[slug]/page.tsx', 'app/robots.ts', 'app/sitemap.ts',
];
function fixture() {
  const dir = mkdtempSync(join(tmpdir(), 'merdian-release-contract-'));
  for (const file of sources) {
    const dest = join(dir, file);
    mkdirSync(dirname(dest), { recursive: true });
    copyFileSync(join(root, file), dest);
  }
  return dir;
}
function run(dir) {
  return spawnSync(process.execPath, [script, '--fixture'], {
    cwd: root,
    encoding: 'utf8',
    env: { ...process.env, NODE_ENV: 'test', MERDIAN_RELEASE_TEST_ROOT: dir },
  });
}
function withFixture(fn) {
  const dir = fixture();
  try { fn(dir); } finally { rmSync(dir, { recursive: true, force: true }); }
}

test('approved company source passes the Vercel public release contract', () => withFixture(dir => {
  const result = run(dir);
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /PUBLIC RELEASE CONTRACT: PASS/);
}));

test('replacing the company homepage with the retired green site fails closed', () => withFixture(dir => {
  writeFileSync(join(dir, 'app/page.tsx'), '<h1>AI infrastructure consulting for companies shipping production LLM systems.</h1>');
  const result = run(dir);
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /retired consulting-only|mi-hero-title/);
}));

test('an incomplete company design, missing a pillar or dark visual system, cannot release', () => withFixture(dir => {
  const page = join(dir, 'app/page.tsx');
  writeFileSync(page, readFileSync(page, 'utf8').replaceAll('VENTURES', 'HIDDEN'));
  let result = run(dir);
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /VENTURES/);
  copyFileSync(join(root, 'app/page.tsx'), page);
  rmSync(join(dir, 'app/merian.css'));
  result = run(dir);
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /Missing public release source/);
}));

test('localhost, unowned domains and legacy brand metadata block release', () => withFixture(dir => {
  const layout = join(dir, 'app/layout.tsx');
  writeFileSync(layout, readFileSync(layout, 'utf8') + '\n// http://localhost:3000 meridian.ai Merdian Intelligence');
  const result = run(dir);
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /localhost/);
  assert.match(result.stderr, /meridian.ai/);
  assert.match(result.stderr, /Merdian Intelligence/);
}));

test('unsubstantiated portfolio promises fail the production gate', () => withFixture(dir => {
  const page = join(dir, 'app/page.tsx');
  writeFileSync(page, readFileSync(page, 'utf8') + '\n// Blabka: More information will be shared');
  const result = run(dir);
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /Blabka/);
}));

test('a same-origin CTA with an external-link affordance is rejected', () => withFixture(dir => {
  const page = join(dir, 'app/page.tsx');
  writeFileSync(page, readFileSync(page, 'utf8').replace('Work with us <span aria-hidden="true">→</span>', 'Work with us <span aria-hidden="true">↗</span>'));
  const result = run(dir);
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /same-origin link uses external-link arrow/);
}));

test('nested information architecture is a production contract', () => withFixture(dir => {
  const page = join(dir, 'app/page.tsx');
  writeFileSync(page, readFileSync(page, 'utf8').replace('02 / CONSULTANCY', '01 / CONSULTANCY'));
  const result = run(dir);
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /02 \/ CONSULTANCY/);
}));

test('an old name in a sibling customer page blocks the release', () => withFixture(dir => {
  const path = join(dir, 'app/products/page.tsx');
  writeFileSync(path, readFileSync(path, 'utf8') + '\n// Merdian Intelligence');
  const result = run(dir);
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /app\/products\/page.tsx: obsolete\/public-invalid Merdian/);
}));

test('missing the canonical Meridian identity fails the release', () => withFixture(dir => {
  const path = join(dir, 'app/layout.tsx');
  writeFileSync(path, readFileSync(path, 'utf8').replaceAll('Meridian Intelligence', 'Other Company'));
  const result = run(dir);
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /missing Meridian Intelligence/);
}));


test('red: illegible light-surface semantic text token cannot deploy', () => withFixture(dir => {
  const path = join(dir, 'app/globals.css');
  const original = readFileSync(path, 'utf8');
  assert.match(original, /--ink-2:\s*#2A2A28/);
  writeFileSync(path, original.replace('--ink-2: #2A2A28', '--ink-2: #F4F4F4'));
  const result = run(dir);
  assert.notEqual(result.status, 0, 'pale editorial text must fail WCAG AA contrast');
  assert.match(result.stderr, /contrast below WCAG AA 4.5:1/);
}));

test('red: removing light-surface editorial override cannot deploy', () => withFixture(dir => {
  const path = join(dir, 'app/merian.css');
  const original = readFileSync(path, 'utf8');
  const match = original.match(/\.mi-manifesto\s+\.mi-eyebrow,\s*\.mi-services\s+\.mi-eyebrow,[\s\S]*?\{\s*color:\s*var\(--ink-2\)\s*\}/);
  assert.ok(match, 'baseline needs the semantic light-surface override');
  writeFileSync(path, original.replace(match[0], '/* disabled light-surface text override */'));
  const result = run(dir);
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /light-surface eyebrow semantic contrast override missing/);
}));

test('red: missing semantic ink token cannot silently pass a source-only gate', () => withFixture(dir => {
  const path = join(dir, 'app/globals.css');
  const original = readFileSync(path, 'utf8');
  writeFileSync(path, original.replace('--ink-2: #2A2A28', '--ink-2-removed: #2A2A28'));
  const result = run(dir);
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /foreground\/background contrast tokens missing/);
}));
