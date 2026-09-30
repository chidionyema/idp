#!/usr/bin/env node
// Builds tokens.json into the three outputs every front end imports. No dependencies, so the
// build is the same on a laptop, in CI and in a Worker build step.
//   dist/tokens.css          CSS custom properties, light on :root, dark via prefers-color-scheme + [data-theme]
//   dist/tailwind.theme.css  Tailwind v4 @theme block mapping utilities to the same variables
//   dist/tokens.ts           typed names for React/Astro islands (values are the CSS variables, never hex)
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const tokens = JSON.parse(readFileSync(join(here, 'tokens.json'), 'utf8'));
mkdirSync(join(here, 'dist'), { recursive: true });

const leaf = (o) => o && typeof o === 'object' && '$value' in o;
const walk = (o, prefix = []) =>
  Object.entries(o)
    .filter(([k]) => !k.startsWith('$'))
    .flatMap(([k, v]) => (leaf(v) ? [[[...prefix, k], v]] : walk(v, [...prefix, k])));

const cssValue = (t) => {
  if (t.$type === 'cubicBezier') return `cubic-bezier(${t.$value.join(',')})`;
  return String(t.$value);
};

// ---- tokens.css --------------------------------------------------------------------------
const colorVars = (theme) =>
  walk(tokens.color[theme]).map(([p, t]) => `  --color-${p.at(-1)}: ${cssValue(t)};`).join('\n');
const nonColor = walk(tokens)
  .filter(([p]) => p[0] !== 'color')
  .map(([p, t]) => `  --${p.join('-')}: ${cssValue(t)};`)
  .join('\n');
const typeExt = walk(tokens.type)
  .map(([p, t]) => {
    const e = t.$extensions?.estate ?? {};
    return [
      `  --type-${p.at(-1)}-lh: ${e.lineHeight ?? '1.5'};`,
      e.letterSpacing ? `  --type-${p.at(-1)}-ls: ${e.letterSpacing};` : null,
    ].filter(Boolean).join('\n');
  })
  .join('\n');

const css = `/* Generated from tokens.json by build.mjs. Do not edit; edit tokens.json. */
:root {
${colorVars('light')}
${nonColor}
${typeExt}
  color-scheme: light;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
${colorVars('dark')}
    color-scheme: dark;
  }
}
:root[data-theme="dark"] {
${colorVars('dark')}
  color-scheme: dark;
}
body { background: var(--color-canvas); color: var(--color-text); font-family: var(--font-sans); font-size: var(--type-md); line-height: var(--type-md-lh); margin: 0; }
@media (prefers-reduced-motion: reduce) { :root { --motion-fast: 0ms; --motion-base: 0ms; } }
`;
writeFileSync(join(here, 'dist/tokens.css'), css);

// ---- tailwind.theme.css -------------------------------------------------------------------
const tw = `/* Generated. Tailwind v4: @import "tailwindcss"; @import "./tailwind.theme.css"; */
@theme {
  --color-*: initial;
${walk(tokens.color.light).map(([p]) => `  --color-${p.at(-1)}: var(--color-${p.at(-1)});`).join('\n')}
  --font-*: initial;
${walk(tokens.font).map(([p]) => `  --font-${p.at(-1)}: var(--font-${p.at(-1)});`).join('\n')}
  --text-*: initial;
${walk(tokens.type).map(([p]) => `  --text-${p.at(-1)}: var(--type-${p.at(-1)});\n  --text-${p.at(-1)}--line-height: var(--type-${p.at(-1)}-lh);`).join('\n')}
  --spacing-*: initial;
${walk(tokens.space).map(([p]) => `  --spacing-${p.at(-1)}: var(--space-${p.at(-1)});`).join('\n')}
  --radius-*: initial;
${walk(tokens.radius).map(([p]) => `  --radius-${p.at(-1)}: var(--radius-${p.at(-1)});`).join('\n')}
  --ease-estate: var(--motion-ease);
  --breakpoint-phone: ${tokens.breakpoint.phone.$value};
  --breakpoint-desktop: ${tokens.breakpoint.desktop.$value};
}
`;
writeFileSync(join(here, 'dist/tailwind.theme.css'), tw);

// ---- tokens.ts ----------------------------------------------------------------------------
const names = walk(tokens.color.light).map(([p]) => p.at(-1));
const ts = `// Generated from tokens.json. Values are CSS variables so a component never carries a hex.
export const color = {
${names.map((n) => `  ${JSON.stringify(n)}: 'var(--color-${n})',`).join('\n')}
} as const;
export type ColorName = keyof typeof color;
export const type = { ${walk(tokens.type).map(([p]) => `${JSON.stringify(p.at(-1))}: 'var(--type-${p.at(-1)})'`).join(', ')} } as const;
export const space = { ${walk(tokens.space).map(([p]) => `${JSON.stringify(p.at(-1))}: 'var(--space-${p.at(-1)})'`).join(', ')} } as const;
export const font = { ${walk(tokens.font).map(([p]) => `${JSON.stringify(p.at(-1))}: 'var(--font-${p.at(-1)})'`).join(', ')} } as const;
export const motion = { ease: 'var(--motion-ease)', fast: 'var(--motion-fast)', base: 'var(--motion-base)' } as const;
export const STATES = ['red', 'needs', 'running', 'good', 'stale', 'blind'] as const;
export type State = (typeof STATES)[number];
export const STATE_WORD: Record<State, string> = { red: 'Red', needs: 'Needs you', running: 'Running', good: 'Good', stale: 'Stale', blind: "Can't check" };
`;
writeFileSync(join(here, 'dist/tokens.ts'), ts);

console.log(`built: ${names.length} colours × 2 themes, ${walk(tokens.type).length} type steps, ${walk(tokens.space).length} space steps → dist/`);
