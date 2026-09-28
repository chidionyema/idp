// Directive-4 sixth note: a red/needs tile must carry who owns it + how long the state has held,
// from data the estate already holds, never invented (rule 13). These two pure helpers feed the
// meta line on a needs-your-hand row. Behaviour-graded by inputs -> words; not look-and-feel (R53).
import { Entity } from '@backstage/catalog-model';
import { heldSinceAgo, ownerOf } from './estate';

const NOW = Date.parse('2026-08-29T12:00:00Z');
const at = (iso: string) => ({ 'estate/health-checked-at': iso });
const entity = (
  spec: Record<string, string>,
  ann?: Record<string, string>,
): Entity => ({
  apiVersion: 'backstage.io/v1alpha1',
  kind: 'Component',
  metadata: { name: 'x', annotations: ann },
  spec,
});

describe('ownerOf (the owner a red tile names)', () => {
  it('reduces a group ref to its bare name', () => {
    expect(ownerOf(entity({ owner: 'group:default/platform' }))).toBe('platform');
  });
  it('keeps a bare owner as-is', () => {
    expect(ownerOf(entity({ owner: 'platform' }))).toBe('platform');
  });
  it('is undefined when the entity names no owner', () => {
    expect(ownerOf(entity({ type: 'founder-surface' }))).toBeUndefined();
  });
});

describe('heldSinceAgo (how long the red/needs state has held)', () => {
  it('says since when a layer records a since (Flux last transition) for the held state', () => {
    expect(heldSinceAgo(entity({}, {}), { since: '2026-08-29T11:56:00Z' }, NOW)).toBe(
      'since 4m ago',
    );
  });
  it('falls back to the last probe recency for a door that records no state since', () => {
    expect(heldSinceAgo(entity({}, at('2026-08-29T11:55:00Z')), {}, NOW)).toBe(
      'last checked 5m ago',
    );
  });
  it('is silent when there is no since and no probe recency to claim', () => {
    expect(heldSinceAgo(entity({}, {}), {}, NOW)).toBeUndefined();
  });
});
