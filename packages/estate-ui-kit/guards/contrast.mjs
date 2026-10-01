#!/usr/bin/env node
// Contrast guard: every text token on every surface token, both themes, WCAG 2.2 SC 1.4.3.
// Text needs 4.5:1. State inks on their own bg need 4.5:1. Accent on canvas needs 4.5:1.
// Exit 1 on the first failure list. Numbers are computed here, not asserted.
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
import { readdirSync, existsSync } from 'node:fs';
const tokens = JSON.parse(readFileSync(join(here, '..', 'tokens.json'), 'utf8'));
// Brands (brands/<name>.json) override colours per theme; each is graded as its own palette.
const brandsDir = join(here, '..', 'brands');
const brands = existsSync(brandsDir) ? readdirSync(brandsDir).filter((f) => f.endsWith('.json')).map((f) => [f.replace(/\.json$/, ''), JSON.parse(readFileSync(join(brandsDir, f), 'utf8'))]) : [];

const lin = (c) => { c /= 255; return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
const lum = (hex) => { const n = parseInt(hex.slice(1), 16); return 0.2126 * lin(n >> 16) + 0.7152 * lin((n >> 8) & 255) + 0.0722 * lin(n & 255); };
const ratio = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };

const failures = [];
let checked = 0;
const palettes = [['kit', {}], ...brands];
for (const [brand, over] of palettes) for (const theme of ['light', 'dark']) {
  const c = { ...Object.fromEntries(Object.entries(tokens.color[theme]).map(([k, v]) => [k, v.$value])), ...(over[theme] ?? {}) };
  const tag = brand === 'kit' ? theme : `${brand}/${theme}`;
  const surfaces = ['canvas', 'surface-1', 'surface-2', 'surface-3'];
  const texts = ['text', 'text-2', 'text-muted', 'accent'];
  for (const s of surfaces) for (const t of texts) {
    const r = ratio(c[t], c[s]); checked++;
    if (r < 4.5) failures.push(`${tag} ${t} on ${s}: ${r.toFixed(2)}:1 (need 4.5)`);
  }
  for (const st of ['red', 'needs', 'running', 'good', 'stale', 'blind']) {
    const r = ratio(c[`state-${st}-ink`], c[`state-${st}-bg`]); checked++;
    if (r < 4.5) failures.push(`${tag} state-${st} ink on bg: ${r.toFixed(2)}:1 (need 4.5)`);
  }
  const r = ratio(c['on-accent'], c.accent); checked++;
  if (r < 4.5) failures.push(`${tag} on-accent on accent: ${r.toFixed(2)}:1 (need 4.5)`);
  const b = ratio(c['border-strong'], c.canvas); checked++;
  if (b < 3) failures.push(`${tag} border-strong on canvas: ${b.toFixed(2)}:1 (need 3, SC 1.4.11)`);
}
if (failures.length) { console.error(`contrast: ${failures.length} of ${checked} pairs fail\n  ` + failures.join('\n  ')); process.exit(1); }
console.log(`contrast: ${checked} pairs checked across ${palettes.length} palette(s) (${palettes.map(([b]) => b).join(', ')}), 0 fail`);
