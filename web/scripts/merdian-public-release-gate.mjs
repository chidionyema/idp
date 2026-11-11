#!/usr/bin/env node
/**
 * MERDIAN PUBLIC RELEASE CONTRACT.
 * Runs from the Vercel project build command, independent of package.json.
 * An obsolete green consulting-only homepage must fail before becoming READY.
 */
import { readFileSync, existsSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

let root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
// Explicit fixture mode exists only for tests; Vercel never supplies this flag.
if (process.argv.includes('--fixture') && process.env.NODE_ENV === 'test' &&
    process.env.MERDIAN_RELEASE_TEST_ROOT) {
  root = resolve(process.env.MERDIAN_RELEASE_TEST_ROOT);
}
const failures = [];
function source(file) {
  const abs = resolve(root, file);
  if (!existsSync(abs)) { failures.push('Missing public release source: ' + file); return ''; }
  return readFileSync(abs, 'utf8');
}
function required(file, value) {
  if (!source(file).includes(value)) failures.push(file + ': missing ' + value);
}
function forbidden(file, value) {
  if (source(file).includes(value)) failures.push(file + ': obsolete/public-invalid ' + value);
}
const canon = 'https://merdian-intelligence.vercel.app';
for (const [file, markers] of Object.entries({
  'app/page.tsx': [
    'mi-hero-title', 'mi-hero', 'INTELLIGENCE', 'MADE', 'REAL',
    '01 / MANIFESTO', '02 / CONSULTANCY', '03 / THE LABORATORY', '04 / VENTURES + PRODUCTS',
    '02.1', '02.2', '02.3', '02.4', '03.1', '03.2', '03.3',
    'CONSULTANCY', 'LABORATORY', 'VENTURES', '/consulting', '/research',
  ],
  'app/layout.tsx': ['./merian.css', 'Merdian Intelligence', 'MERDIAN_SITE_URL'],
  'app/merian.css': ['.mi-hero', '.mi-header', '.mi-footer', '.mi-interior', 'prefers-reduced-motion', '.mi-services .mi-eyebrow', 'color:#6b4a16', '.mi-hero-actions', '.mi-art-label-top'],
  'components/Nav.tsx': ['mi-header', 'mi-nav-links', 'Consultancy', 'Laboratory', 'Ventures', 'mi-mobile-panel'],
  'components/Footer.tsx': ['mi-footer', 'MERDIAN INTELLIGENCE'],
  'app/products/page.tsx': ['mi-interior', 'Mumchimp', 'Genesis'],
  'app/consulting/page.tsx': ['mi-interior', 'Applied AI engineering'],
  'app/contact/page.tsx': ['mi-interior', 'validateContact(form)'],
  'app/robots.ts': ['MERDIAN_SITE_URL'],
  'app/sitemap.ts': ['MERDIAN_SITE_URL'],
})) {
  for (const marker of markers) required(file, marker);
}
for (const file of [
  'app/page.tsx', 'app/layout.tsx', 'components/Nav.tsx', 'components/Footer.tsx',
  'app/consulting/page.tsx', 'app/robots.ts', 'app/sitemap.ts',
]) {
  forbidden(file, 'meridian.ai');
  forbidden(file, 'Meridian Intelligence');
}
// Content debt and false affordances are release failures, not editorial follow-up.
for (const file of ['app/page.tsx', 'app/products/page.tsx']) {
  for (const phrase of ['Blabka', 'More information will be shared', 'Further details will be published', 'Part of the Merdian product portfolio.']) {
    forbidden(file, phrase);
  }
}
for (const file of ['app/page.tsx','app/layout.tsx','app/robots.ts','app/sitemap.ts']) {
  forbidden(file, 'http://localhost');
}
for (const file of ['app/page.tsx','app/layout.tsx']) {
  forbidden(file, 'AI infrastructure consulting for companies shipping production LLM systems');
}
for (const file of ['app/layout.tsx','app/robots.ts','app/sitemap.ts']) {
  required(file, canon);
}
// A directional external-link glyph on same-origin navigation is misleading.
for (const file of ['app/page.tsx', 'app/products/page.tsx']) {
  const markup = source(file);
  const internal = /<(?:Link|a)\b[^>]*href=["']\/(?!\/)[^"']*["'][^>]*>[\s\S]*?<\/(?:Link|a)>/g;
  for (const link of markup.matchAll(internal)) {
    if (link[0].includes('↗')) failures.push(file + ': same-origin link uses external-link arrow ↗');
  }
}
if (!source('app/page.tsx').includes('href="/consulting"') || !source('app/page.tsx').includes('href="/research"')) {
  failures.push('app/page.tsx: customer consultancy and laboratory links missing');
}
if (failures.length) {
  console.error('MERDIAN PUBLIC RELEASE REJECTED (' + failures.length + ' failures)');
  for (const item of failures) console.error(' - ' + item);
  console.error('Keep public aliases pinned to the last independently verified build.');
  process.exitCode = 1;
} else {
  console.log('MERDIAN PUBLIC RELEASE CONTRACT: PASS');
  console.log('Premium identity, consultancy/laboratory/ventures and canonical URLs confirmed.');
}
