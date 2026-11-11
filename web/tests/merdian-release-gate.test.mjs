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
  'app/page.tsx', 'app/layout.tsx', 'app/merian.css',
  'components/Nav.tsx', 'components/Footer.tsx',
  'app/products/page.tsx', 'app/consulting/page.tsx',
  'app/fieldbooks/page.tsx', 'app/fieldbooks/from-prompt-to-proof/page.tsx', 'lib/commercialStorefront.ts',
  'app/contact/page.tsx', 'app/robots.ts', 'app/sitemap.ts',
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

test('localhost and unowned Meridian metadata are release blocking, not warnings', () => withFixture(dir => {
  const layout = join(dir, 'app/layout.tsx');
  writeFileSync(layout, readFileSync(layout, 'utf8') + '\n// http://localhost:3000 meridian.ai Meridian Intelligence');
  const result = run(dir);
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /localhost/);
  assert.match(result.stderr, /meridian.ai/);
  assert.match(result.stderr, /Meridian Intelligence/);
}));
