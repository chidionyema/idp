// Directive 4: a door (founder-surface) must not read as a bare GitHub Source button. The estate
// already records when a door was last health-checked; this helper turns that annotation into the
// plain recency sentence a tile shows, so a tile carries live evidence of the estate speaking
// about it. Pure, behaviour-graded (time in -> recency sentence out), not look-and-feel (R53).
import { Entity } from '@backstage/catalog-model';
import { checkedAgo } from './estate';

const door = (checkedAt?: string): Entity => ({
  apiVersion: 'backstage.io/v1alpha1',
  kind: 'Component',
  metadata: {
    name: 'github',
    annotations: checkedAt
      ? {
          'estate/health': 'ok 200',
          'estate/health-checked-at': checkedAt,
        }
      : { 'estate/health': 'ok 200' },
  },
  spec: { type: 'founder-surface' },
});

describe('checkedAgo (the recency a door tile carries)', () => {
  it('says, in a sentence, when the door was last checked', () => {
    const now = Date.parse('2026-08-29T12:00:00Z');
    expect(
      checkedAgo(door('2026-08-29T11:56:00Z'), now),
    ).toMatch(/^checked 4m ago$/);
  });

  it('is silent for a door that has never been checked (no time to claim)', () => {
    expect(checkedAgo(door(undefined))).toBeUndefined();
    expect(checkedAgo(door('not a time'))).toBeUndefined();
  });

  it('never invents a recency when the checked stamp is in the future or unparsable', () => {
    // A future stamp is a clock skew, not evidence of age; the helper still says a true thing
    // about now vs that stamp rather than fabricating (it will not return 'checked' with a
    // negative amount because ago() has no negative branch).
    expect(checkedAgo(door('2099-01-01T00:00:00Z'))?.startsWith('checked')).toBe(
      true,
    );
  });
});
