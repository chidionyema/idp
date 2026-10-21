/*
 * The face says how old its news is (idp#6784). The failure was a week-old claim and a cached
 * /estate both reading like live news; these pin the age words and, above all, that a source with
 * no usable time is `unknown` and never `fresh`.
 */
import {
  ageLabel,
  atMs,
  CLAIM_STALE_MS,
  ESTATE_STALE_MS,
  freshness,
} from './faceFreshness';

const NOW = Date.parse('2026-10-21T12:00:00Z');
const ago = (ms: number) => new Date(NOW - ms).toISOString();
const MIN = 60 * 1000;
const H = 60 * MIN;

describe('ageLabel', () => {
  it('says just now under a minute, and for a clock slightly ahead of ours', () => {
    expect(ageLabel(ago(10 * 1000), NOW)).toBe('just now');
    expect(ageLabel(ago(-5 * MIN), NOW)).toBe('just now');
  });
  it('counts minutes, then hours, then days', () => {
    expect(ageLabel(ago(4 * MIN), NOW)).toBe('4 min ago');
    expect(ageLabel(ago(3 * H), NOW)).toBe('3 h ago');
    expect(ageLabel(ago(47 * H), NOW)).toBe('47 h ago');
    expect(ageLabel(ago(72 * H), NOW)).toBe('3 d ago');
  });
  it('has no age for a missing or unreadable time', () => {
    expect(ageLabel(undefined, NOW)).toBeNull();
    expect(ageLabel('', NOW)).toBeNull();
    expect(ageLabel('last tuesday', NOW)).toBeNull();
  });
});

describe('freshness', () => {
  it('is fresh inside the source\'s window and stale past it', () => {
    expect(freshness(ago(5 * MIN), NOW, ESTATE_STALE_MS)).toBe('fresh');
    expect(freshness(ago(11 * MIN), NOW, ESTATE_STALE_MS)).toBe('stale');
    expect(freshness(ago(20 * H), NOW, CLAIM_STALE_MS)).toBe('fresh');
    expect(freshness(ago(30 * H), NOW, CLAIM_STALE_MS)).toBe('stale');
  });
  it('the same age is fresh for a claim and stale for the vitals: the windows are per source', () => {
    expect(freshness(ago(2 * H), NOW, CLAIM_STALE_MS)).toBe('fresh');
    expect(freshness(ago(2 * H), NOW, ESTATE_STALE_MS)).toBe('stale');
  });
  it('a source that cannot date itself is unknown, never fresh', () => {
    expect(freshness(undefined, NOW, ESTATE_STALE_MS)).toBe('unknown');
    expect(freshness('garbage', NOW, CLAIM_STALE_MS)).toBe('unknown');
    expect(atMs(null)).toBeNull();
  });
});
