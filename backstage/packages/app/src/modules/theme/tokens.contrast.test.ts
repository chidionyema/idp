// The six state tints are the page's whole grammar: a pill's fill and its border are how the
// founder reads Red from Good at a glance on a phone. Measured 2026-08-31, every one of the
// twenty-four edge/canvas pairs failed WCAG 2.2 SC 1.4.11 Non-text Contrast (3:1) -- the worst
// was stateLight.needs at 1.30:1, a border the eye cannot find on white. The ink was never the
// problem: all twelve ink values already cleared 4.5:1. This file is why that cannot come back.
//
// SC 1.4.11 applies to the boundary because the boundary is what carries the state. The fill
// stays a soft tint on purpose -- it is decoration behind text that is already contrast-checked
// against it, which is the exception the success criterion names.
import { dark, light, stateDark, stateLight, STATE_ORDER } from './tokens';

/** WCAG 2.x relative luminance. sRGB channel, linearised, then the 0.2126/0.7152/0.0722 sum. */
function luminance(hex: string): number {
  const h = hex.replace('#', '');
  const channels = [0, 2, 4].map(i => parseInt(h.slice(i, i + 2), 16) / 255);
  const linear = channels.map(c =>
    c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4,
  );
  return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
}

/** WCAG 2.x contrast ratio, (lighter + 0.05) / (darker + 0.05). */
function ratio(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

// Two values with a known published ratio, so a bug in the maths above fails here first
// rather than silently passing every colour in the file (LAW 15: the instrument is checked).
describe('the contrast maths itself', () => {
  it('scores black on white at 21:1 and a colour against itself at 1:1', () => {
    expect(ratio('#000000', '#ffffff')).toBeCloseTo(21, 2);
    expect(ratio('#0b0c0e', '#0b0c0e')).toBeCloseTo(1, 5);
  });
  it('scores the WCAG reference pair #767676 on white at 4.54:1', () => {
    expect(ratio('#767676', '#ffffff')).toBeCloseTo(4.54, 1);
  });
});

const THEMES = [
  { name: 'dark', canvas: dark.canvas, tints: stateDark },
  { name: 'light', canvas: light.canvas, tints: stateLight },
] as const;

describe.each(THEMES)('$name theme state tints', ({ canvas, tints }) => {
  // SC 1.4.11 Non-text Contrast: 3:1 for the boundary of a component that carries meaning.
  it.each(STATE_ORDER)('%s: the edge is findable against the canvas (3:1)', state => {
    expect(ratio(tints[state].edge, canvas)).toBeGreaterThanOrEqual(3);
  });

  // SC 1.4.3 Contrast (Minimum): 4.5:1 for body text, against the surface it actually sits on
  // and against the canvas, because the same ink is used on both.
  it.each(STATE_ORDER)('%s: the ink is readable on its own tint (4.5:1)', state => {
    expect(ratio(tints[state].ink, tints[state].bg)).toBeGreaterThanOrEqual(4.5);
  });
  it.each(STATE_ORDER)('%s: the ink is readable on the bare canvas (4.5:1)', state => {
    expect(ratio(tints[state].ink, canvas)).toBeGreaterThanOrEqual(4.5);
  });

  // A state nobody can tell apart from its neighbour is not six states, it is one. Every pair
  // of edges must differ, or a redesign can quietly collapse two of them into the same hex.
  it('gives the six states six different edges', () => {
    const edges = STATE_ORDER.map(s => tints[s].edge);
    expect(new Set(edges).size).toBe(STATE_ORDER.length);
  });
});
