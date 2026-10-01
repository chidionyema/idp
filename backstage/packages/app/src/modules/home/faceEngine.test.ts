import { wordTimings } from './faceEngine';

describe('wordTimings', () => {
  it('spreads every word across the clause, in order, inside the audio', () => {
    const t = wordTimings('The estate is live, founder.', 2000);
    expect(t.words).toEqual(['The', 'estate', 'is', 'live,', 'founder.']);
    expect(t.wtimes[0]).toBeGreaterThan(0);
    for (let i = 1; i < t.wtimes.length; i++) expect(t.wtimes[i]).toBeGreaterThan(t.wtimes[i - 1]);
    const end = t.wtimes[t.wtimes.length - 1] + t.wdurations[t.wdurations.length - 1];
    expect(end).toBeLessThanOrEqual(2000);
    expect(end).toBeGreaterThan(1900);
  });

  it('gives a long word more time than a short one', () => {
    const t = wordTimings('a extraordinary', 1000);
    expect(t.wdurations[1]).toBeGreaterThan(t.wdurations[0] * 3);
  });

  it('says nothing for an empty clause or no audio', () => {
    expect(wordTimings('   ', 1000).words).toEqual([]);
    expect(wordTimings('hello', 0).words).toEqual([]);
  });
});
