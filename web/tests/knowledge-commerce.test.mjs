import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const src = file => readFileSync(new URL('../' + file, import.meta.url), 'utf8');

test('the premium homepage keeps its approved identity while advertising a real knowledge product', () => {
  const home = src('app/page.tsx');
  for (const required of ['mi-hero-title', 'INTELLIGENCE', 'MADE', 'REAL', 'CONSULTANCY', 'LABORATORY', 'VENTURES', 'Mumchimp', 'Genesis', 'Blabka', 'href="/fieldbooks"']) {
    assert.ok(home.includes(required), 'missing source evidence: ' + required);
  }
  assert.ok(!home.includes('gumroad.com'), 'homepage must not invent merchant checkout URLs');
  assert.ok(!home.includes('github.com'), 'company customers must not be redirected to source code');
});

test('Fieldbooks has a real read-only publication and cannot fabricate a merchant checkout', () => {
  const page = src('app/fieldbooks/page.tsx');
  const chapter = src('app/fieldbooks/from-prompt-to-proof/page.tsx');
  assert.ok(page.includes('verifiedGumroadProductUrl(process.env.MERDIAN_GUMROAD_FIELD_GUIDE_URL)'));
  assert.ok(page.includes('MERCHANT CONNECTION PENDING'));
  assert.ok(page.includes('Purchasing is not enabled yet.'));
  assert.ok(page.includes('href="/fieldbooks/from-prompt-to-proof"'));
  assert.ok(chapter.includes('The model') || chapter.includes('THE MODEL'));
  assert.ok(chapter.includes('failureTests'));
  assert.ok(chapter.includes('Lost-instruction test'));
  assert.ok(chapter.includes('Revoked-authority test'));
  assert.ok(chapter.includes('False-green test'));
  assert.ok(chapter.includes('Double-effect test'));
  assert.ok(chapter.includes('Release-regression test'));
  assert.ok(!page.includes('https://gumroad.com/l/'), 'fabricated product checkout must not enter source');
  assert.ok(!page.includes('https://merdian.gumroad.com/l/'), 'fabricated merchant subdomain must not enter source');
});

test('knowledge-commerce routes are discoverable and canonical while legal entity is unregistered', () => {
  const nav = src('components/Nav.tsx');
  const footer = src('components/Footer.tsx');
  const sitemap = src('app/sitemap.ts');
  assert.ok(nav.includes('href: "/fieldbooks"'));
  assert.ok(footer.includes('href="/fieldbooks"'));
  assert.ok(sitemap.includes('/fieldbooks/from-prompt-to-proof'));
  assert.ok(!src('app/fieldbooks/page.tsx').includes('Ltd.'), 'do not assert an unregistered company');
  assert.ok(!src('app/fieldbooks/page.tsx').includes('Registered number'), 'do not invent corporate identity');
});

test('premium knowledge headings must remain legible against dark background', () => {
  const css=src('app/fieldbooks/fieldbooks.css');
  const chapter=css.split('.mi-chapter-hero h1{')[1]?.split('}')[0] ?? '';
  const collection=css.split('.mi-knowledge-hero h1{')[1]?.split('}')[0] ?? '';
  assert.ok(chapter.includes('color:#fff'), 'chapter heading lost its explicit light foreground');
  assert.ok(collection.includes('color:#fff'), 'collection heading lost its explicit light foreground');
});
