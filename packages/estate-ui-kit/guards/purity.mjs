#!/usr/bin/env node
// Token-purity guard. Usage: node guards/purity.mjs <dir-or-file>...
// Refuses, in .css/.scss/.tsx/.jsx/.astro/.svelte/.vue files (skipping node_modules, dist, .next,
// and the kit's own tokens.json/tokens.css which are the only places a literal may live):
//   1. colour literals: #hex, rgb(), hsl(), oklch()
//   2. font-size with a px/rem literal instead of var(--type-*)
//   3. inline style="" attributes carrying a colour or font-size
// Prints every hit as file:line and exits 1 if any. This is the gate crew#694 CP4 asks for.
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, extname, basename } from 'node:path';

const EXT = new Set(['.css', '.scss', '.tsx', '.jsx', '.astro', '.svelte', '.vue']);
const SKIP = new Set(['node_modules', 'dist', '.next', '.astro', 'storybook-static', 'build', 'target']);
const ALLOW_FILE = /^(tokens\.(json|css|ts)|tailwind\.theme\.css)$/;
const files = [];
const collect = (p) => {
  const st = statSync(p);
  if (st.isDirectory()) { if (!SKIP.has(basename(p))) for (const e of readdirSync(p)) collect(join(p, e)); }
  else if (EXT.has(extname(p)) && !ALLOW_FILE.test(basename(p))) files.push(p);
};
for (const a of process.argv.slice(2)) collect(a);

const COLOR = /(#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?|oklch)\()/;
const FONTSIZE = /font-size\s*:\s*(\d*\.?\d+)(px|rem|em|pt)/;
const INLINE = /style\s*=\s*["'{][^"'}]*(color|font-size)\s*:/;
const hits = [];
for (const f of files) {
  const lines = readFileSync(f, 'utf8').split('\n');
  lines.forEach((line, i) => {
    if (/^\s*(\/\/|\/\*|\*|`|\{\/\*)/.test(line)) return; // comments and template text may mention hex
    line = line.replace(/\/\*.*?\*\//g, '').replace(/\/\/.*$/, '');
    const where = `${f}:${i + 1}`;
    if (COLOR.test(line) && !/url\(|#\w+\s*\{|href=|id=|key=/.test(line)) hits.push(`${where}  colour literal   ${line.trim().slice(0, 90)}`);
    if (FONTSIZE.test(line) && !/var\(--type-/.test(line)) hits.push(`${where}  off-scale size   ${line.trim().slice(0, 90)}`);
    if (INLINE.test(line)) hits.push(`${where}  inline style     ${line.trim().slice(0, 90)}`);
  });
}
const counts = hits.reduce((m, h) => { const k = h.split(/\s{2,}/)[1]; m[k] = (m[k] || 0) + 1; return m; }, {});
if (hits.length) {
  console.error(`purity: ${hits.length} violations in ${files.length} files — ` + Object.entries(counts).map(([k, v]) => `${k}: ${v}`).join(', '));
  console.error(hits.slice(0, 40).map((h) => '  ' + h).join('\n') + (hits.length > 40 ? `\n  … ${hits.length - 40} more` : ''));
  process.exit(1);
}
console.log(`purity: ${files.length} files, 0 violations`);
