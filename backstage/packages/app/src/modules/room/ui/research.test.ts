// The research panel's pure helpers: the pill's words, a claim's age and its tone. The states
// these functions produce are the difference between "the engine has found nothing" and "nobody
// could look" -- an outage must never render as an empty department.
import { ago, summary, toneOf, type Board } from './ResearchFindings';

describe('ago', () => {
  const now = Date.parse('2026-10-10T14:00:00Z');
  it('words the age of a claim in plain units', () => {
    expect(ago('2026-10-10T13:59:30Z', now)).toBe('just now');
    expect(ago('2026-10-10T13:25:00Z', now)).toBe('35 min ago');
    expect(ago('2026-10-10T09:00:00Z', now)).toBe('5 h ago');
    expect(ago('2026-10-08T14:00:00Z', now)).toBe('2 d ago');
  });
  it('says so rather than showing NaN for a timestamp that did not parse', () => {
    expect(ago('', now)).toBe('at an unknown time');
    expect(ago('not-a-timestamp', now)).toBe('at an unknown time');
  });
});

describe('summary', () => {
  const board: Board = { available: true, count: 3, claims: [] };
  it('names each state in its own words', () => {
    expect(summary(null, null)).toBe('research · …');
    expect(summary(null, 'boom')).toBe('research · unreachable');
    expect(summary({ available: false, error: 'down' }, null)).toBe('research · unreadable');
    expect(summary({ available: true, count: 0, claims: [] }, null)).toBe(
      'research · no findings yet',
    );
    expect(summary(board, null)).toBe('research · 3 findings');
    expect(summary({ available: true, count: 1, claims: [] }, null)).toBe('research · 1 finding');
  });
});

describe('toneOf', () => {
  it('never carries the state in colour alone -- but the colour still follows the word', () => {
    expect(toneOf('verified')).toContain('emerald');
    expect(toneOf('VERIFIED')).toContain('emerald');
    expect(toneOf('failed')).toContain('rose');
    expect(toneOf('rejected')).toContain('rose');
    expect(toneOf('pending')).toContain('amber');
    expect(toneOf('')).toContain('amber');
  });
});
