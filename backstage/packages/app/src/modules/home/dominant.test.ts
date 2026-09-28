// Directive 1: the home page leads with a dominant state, so a founder reads the estate's
// condition from across the room, not from a 17px sentence. `dominantState` is that mark's
// pure heart: given a k8s/Flux state count, it returns the single worst present state that
// must lead the page, or `good` when every checked item is healthy. These tests grade that
// cartography (which state leads, in what order, at the boundaries), not look-and-feel (R53).
import { Counts, dominantState } from './estate';

const c = (over: Partial<Counts> = {}): Counts => ({
  red: 0,
  needs: 0,
  running: 0,
  good: 0,
  stale: 0,
  blind: 0,
  ...over,
});

describe('dominantState (the mark the page must lead with)', () => {
  it('leads with red when anything is red, whatever else is also present', () => {
    expect(
      dominantState(c({ red: 1, good: 40, blind: 3, stale: 2 })),
    ).toBe('red');
    expect(dominantState(c({ red: 1 }))).toBe('red');
  });

  it('leads with needs before stale, blind, running or good (worst-first, no red)', () => {
    expect(dominantState(c({ needs: 1, stale: 4, running: 5, good: 1 }))).toBe(
      'needs',
    );
    expect(
      dominantState(c({ needs: 2, blind: 1, running: 1, good: 3 })),
    ).toBe('needs');
  });

  it('never lets an unchecked (blind) or mid-change (running) item be hidden behind good', () => {
    expect(dominantState(c({ blind: 1, good: 9 }))).toBe('blind');
    expect(dominantState(c({ running: 1, good: 2 }))).toBe('running');
    expect(dominantState(c({ running: 3 }))).toBe('running');
  });

  it('says good only when every checked item is good', () => {
    expect(dominantState(c({ good: 31 }))).toBe('good');
    expect(dominantState(c({}))).toBe('good');
  });

  it('orders worst-first exactly as the state rank orders the bands', () => {
    // None of the present states may be skipped: the leader is the rank minimum.
    const states: Array<[Counts, string]> = [
      [c({ red: 1 }), 'red'],
      [c({ needs: 1 }), 'needs'],
      [c({ stale: 1 }), 'stale'],
      [c({ blind: 1 }), 'blind'],
      [c({ running: 1 }), 'running'],
      [c({ good: 1 }), 'good'],
    ];
    for (const [counts, expected] of states) {
      expect(dominantState(counts)).toBe(expected);
    }
  });
});
