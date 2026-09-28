// The estate's palette, named once (crew#459 redesign, 2026-08-29). Every module that paints
// imports these; no other file carries a colour literal.
//
// The posture is a quiet instrument, not a dashboard: a near-black canvas, hairline borders
// instead of shadows, one accent for chrome, and colour spent only on state. Every state ships
// as a dot, a word and a tint, so colour never carries a meaning alone (WCAG 1.4.1).

export type Tone = {
  canvas: string;
  surface1: string;
  surface2: string;
  surface3: string;
  borderSubtle: string;
  border: string;
  borderStrong: string;
  textPrimary: string;
  textSecondary: string;
  textMuted: string;
  accent: string;
  accentPressed: string;
  inkOnAccent: string;
};

export const dark: Tone = {
  canvas: '#0b0c0e',
  surface1: '#121316',
  surface2: '#17191d',
  surface3: '#1c1f24',
  borderSubtle: '#232629',
  border: '#2e3238',
  borderStrong: '#3b4048',
  textPrimary: '#f2f4f7',
  textSecondary: '#a8afba',
  textMuted: '#7a828e',
  accent: '#4c8dff',
  accentPressed: '#3b79e6',
  inkOnAccent: '#0b0c0e',
};

export const light: Tone = {
  canvas: '#ffffff',
  surface1: '#f9fafb',
  surface2: '#ffffff',
  surface3: '#f2f4f7',
  borderSubtle: '#edeff2',
  border: '#e4e7ec',
  borderStrong: '#d0d5dd',
  textPrimary: '#0b0c0e',
  textSecondary: '#4a515c',
  textMuted: '#667085',
  accent: '#175cd3',
  accentPressed: '#0f4bb5',
  inkOnAccent: '#ffffff',
};

// The six states and their words. `blind` is drawn hollow and is never green: a thing nobody
// could check is the most expensive state in the estate, not a neutral one.
export type State = 'red' | 'needs' | 'running' | 'good' | 'stale' | 'blind';
export const STATE_ORDER: State[] = [
  'red',
  'needs',
  'stale',
  'blind',
  'running',
  'good',
];
export const STATE_WORD: Record<State, string> = {
  red: 'Red',
  needs: 'Needs you',
  running: 'Running',
  good: 'Good',
  stale: 'Stale',
  blind: "Can't check",
};
export type StateTint = { ink: string; bg: string; edge: string };
// EDGE CONTRAST, 2026-08-31. Every one of these twelve `edge` values was measured against its
// own canvas and all twelve failed WCAG 2.2 SC 1.4.11 Non-text Contrast (3:1) -- stateLight.needs
// was the worst at 1.30:1, a border nobody can see on white. The pill's border is what carries
// the state, so it is the boundary the criterion is about. Each one was raised by lightness only:
// the hue and saturation are the originals, so the palette reads the same and the shape is now
// findable. The `ink` values are untouched; all twelve already cleared 4.5:1. Held by
// tokens.contrast.test.ts, which fails on the old values.

export const stateDark: Record<State, StateTint> = {
  red: { ink: '#ff5c5c', bg: '#2a1214', edge: '#a43b42' },
  needs: { ink: '#ffb020', bg: '#2a1e08', edge: '#7b5915' },
  running: { ink: '#4c8dff', bg: '#101a2e', edge: '#375ea3' },
  good: { ink: '#3ecf8e', bg: '#0e241b', edge: '#2b6a50' },
  stale: { ink: '#a78bfa', bg: '#1c1730', edge: '#6751a3' },
  blind: { ink: '#8a93a0', bg: '#1a1c20', edge: '#57606c' },
};
export const stateLight: Record<State, StateTint> = {
  red: { ink: '#b42318', bg: '#fef3f2', edge: '#fc5e55' },
  needs: { ink: '#b54708', bg: '#fffaeb', edge: '#bd8b02' },
  running: { ink: '#175cd3', bg: '#eff8ff', edge: '#1296ff' },
  good: { ink: '#067647', bg: '#ecfdf3', edge: '#20a957' },
  stale: { ink: '#6941c6', bg: '#f4f3ff', edge: '#8d84fc' },
  blind: { ink: '#475467', bg: '#f9fafb', edge: '#8894a9' },
};

// Backstage's own palette.status keys, fed from the same six colours so the vendor's
// components (chips, tables, entity pages) speak the same language as the front page.
export const statusLight = {
  ok: stateLight.good.ink,
  warning: stateLight.needs.ink,
  error: stateLight.red.ink,
  pending: stateLight.blind.ink,
  running: stateLight.running.ink,
  aborted: stateLight.stale.ink,
};
export const statusDark = {
  ok: stateDark.good.ink,
  warning: stateDark.needs.ink,
  error: stateDark.red.ink,
  pending: stateDark.blind.ink,
  running: stateDark.running.ink,
  aborted: stateDark.stale.ink,
};

// Names the wordmark and the sign-in page still use.
export const accent = dark.accent;
export const accentSoft = '#8fb5ff';
export const navy = dark.canvas;
export const navyRaised = dark.surface2;
export const paperWarm = light.canvas;
export const inkOnAccent = dark.inkOnAccent;
export const inkOnNavy = dark.textPrimary;

// System faces first: the portal must look native on the founder's phone and a buyer's
// laptop without a font download that a proxy or a slow link can drop.
export const fontFamily =
  '-apple-system, BlinkMacSystemFont, "SF Pro Text", Inter, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif';
export const monoFamily =
  'ui-monospace, SFMono-Regular, "SF Mono", "JetBrains Mono", Menlo, monospace';
export const ease = 'cubic-bezier(.2,.8,.2,1)';
export const phone = '@media (max-width: 600px)';
export const desktop = '@media (min-width: 1024px)';
export const reducedMotion = '@media (prefers-reduced-motion: reduce)';
