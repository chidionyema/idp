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
    'CONSULTANCY', 'LABORATORY', 'VENTURES', '/consulting', '/research',
  ],
  'app/layout.tsx': ['./merian.css', 'Merdian Intelligence', 'MERDIAN_SITE_URL'],
  'app/merian.css': ['.mi-hero', '.mi-header', '.mi-footer', '.mi-interior', 'prefers-reduced-motion'],
  'components/Nav.tsx': ['mi-header', 'mi-nav-links', 'Consultancy', 'Laboratory', 'Ventures', 'mi-mobile-panel'],
  'components/Footer.tsx': ['mi-footer', 'MERDIAN INTELLIGENCE'],
  'app/products/page.tsx': ['mi-interior', 'Mumchimp'],
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
for (const file of ['app/page.tsx','app/layout.tsx','app/robots.ts','app/sitemap.ts']) {
  forbidden(file, 'http://localhost');
}
for (const file of ['app/page.tsx','app/layout.tsx']) {
  forbidden(file, 'AI infrastructure consulting for companies shipping production LLM systems');
}
for (const file of ['app/layout.tsx','app/robots.ts','app/sitemap.ts']) {
  required(file, canon);
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
