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
const canon = 'https://meridian-intelligence-uk.vercel.app';
for (const [file, markers] of Object.entries({
  'app/page.tsx': [
    'mi-hero-title', 'mi-hero', 'INTELLIGENCE', 'MADE', 'REAL',
    '01 / MANIFESTO', '02 / CONSULTANCY', '03 / THE LABORATORY', '04 / VENTURES + PRODUCTS',
    '02.1', '02.2', '02.3', '02.4', '03.1', '03.2', '03.3',
    'CONSULTANCY', 'LABORATORY', 'VENTURES', '/consulting', '/research', 'Chronos', '/products/chronos',
  ],
  'app/layout.tsx': ['./merian.css', 'Meridian Intelligence', 'MERIDIAN_SITE_URL'],
  'app/merian.css': ['.mi-hero', '.mi-header', '.mi-footer', '.mi-interior', 'prefers-reduced-motion', '.mi-services .mi-eyebrow', '.mi-hero-actions', '.mi-art-label-top', '.mi-chronos-hero'],
  'components/Nav.tsx': ['mi-header', 'mi-nav-links', 'Consultancy', 'Laboratory', 'Ventures', 'mi-mobile-panel'],
  'components/Footer.tsx': ['mi-footer', 'MERIDIAN INTELLIGENCE'],
  'app/products/page.tsx': ['mi-interior', 'Mumchimp', 'Genesis', 'Chronos', '/products/chronos', 'NOT GENERALLY AVAILABLE'],
  'app/products/chronos/page.tsx': ['mi-interior mi-chronos', 'CHRONOS', 'RESEARCH CONCEPT', 'NOT GENERALLY AVAILABLE', '/contact'],
  'app/consulting/page.tsx': ['mi-interior', 'Applied AI engineering'],
  'app/contact/page.tsx': ['mi-interior', 'validateContact(form)'],
  'app/robots.ts': ['MERDIAN_SITE_URL'],
  'app/sitemap.ts': ['MERDIAN_SITE_URL'],
})) {
  for (const marker of markers) required(file, marker);
}
for (const file of [
  'app/page.tsx', 'app/layout.tsx', 'components/Nav.tsx', 'components/Footer.tsx',
  'app/consulting/page.tsx', 'app/products/chronos/page.tsx', 'app/robots.ts', 'app/sitemap.ts',
]) {
  forbidden(file, 'meridian.ai');
  forbidden(file, 'Merdian Intelligence');
}
// Light-surface editorial labels must remain legible after visual redesign.
// Resolve the approved semantic token instead of pinning an arbitrary old CSS
// literal that blocked a verified new visual system in Vercel build b3c6c35.
const globals = source('app/globals.css');
const css = source('app/merian.css');
const inkToken = globals.match(/--ink-2\s*:\s*(#[0-9a-f]{6})\s*;/i);
const bgToken = globals.match(/--bg\s*:\s*(#[0-9a-f]{6})\s*;/i);
if (!/\.mi-manifesto\s+\.mi-eyebrow,\s*\.mi-services\s+\.mi-eyebrow,[\s\S]*?\{\s*color:\s*var\(--ink-2\)\s*\}/.test(css)) {
  failures.push('app/merian.css: light-surface eyebrow semantic contrast override missing');
}
function luminance(hex) {
  const channels = [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16) / 255);
  const values = channels.map(v => v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4);
  return values[0] * 0.2126 + values[1] * 0.7152 + values[2] * 0.0722;
}
if (!inkToken || !bgToken) {
  failures.push('app/globals.css: light-surface foreground/background contrast tokens missing');
} else {
  const ink = luminance(inkToken[1]);
  const bg = luminance(bgToken[1]);
  const ratio = (Math.max(ink, bg) + 0.05) / (Math.min(ink, bg) + 0.05);
  if (ratio < 4.5) {
    failures.push('app/globals.css: light-surface eyebrow contrast below WCAG AA 4.5:1');
  }
}

// Visitor-facing corporate identity must not regress to the deprecated spelling.
// Legacy environment variable names are permitted for compatibility, but visible copy is not.
for (const file of [
  'app/page.tsx', 'app/layout.tsx', 'app/manifest.ts', 'app/opengraph-image.tsx',
  'components/Logo.tsx', 'components/Nav.tsx', 'components/Footer.tsx',
  'content/site.ts', 'app/products/page.tsx', 'app/research/page.tsx',
  'app/consulting/page.tsx', 'app/contact/page.tsx', 'app/contact/layout.tsx',
  'app/case-studies/page.tsx', 'app/tooling/page.tsx', 'app/writing/page.tsx',
  'app/products/chronos/page.tsx',
  'app/writing/[slug]/page.tsx',
]) {
  forbidden(file, 'Merdian');
  forbidden(file, 'MERDIAN INTELLIGENCE');
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
