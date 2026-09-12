import {
  headroomLabel,
  isPinned,
  placementState,
  requestLabel,
  summarisePlacement,
} from './placement';
import type { PlacementPod } from './placement';

const pod = (over: Partial<PlacementPod> = {}): PlacementPod => ({
  namespace: 'backstage',
  name: 'catalogue-abc',
  kind: 'Deployment',
  cpu_request_m: 250,
  memory_request_mi: 512,
  unschedulable: false,
  best_other_cpu_free_m: 900,
  best_other_memory_free_mi: 2048,
  reason: null,
  ...over,
});

describe('placement tells three different facts apart', () => {
  it('a pod the scheduler refused is first, because it is not running at all', () => {
    const s = summarisePlacement({
      pods: [pod({ unschedulable: true, reason: '0/2 nodes are available: 2 Insufficient cpu' })],
    });
    expect(s.refused).toHaveLength(1);
    expect(s.summary).toContain('the scheduler refused');
    // An outage outranks a risk. A page that led with "pinned" while a pod was not running would
    // be leading with the lesser of the two facts.
    expect(s.summary.indexOf('refused')).toBeLessThan(
      s.summary.indexOf('pinned') === -1 ? 999 : s.summary.indexOf('pinned'),
    );
  });

  it('a pod that fits no other node is pinned, not healthy', () => {
    // This is the ClickHouse state: running, looks fine, and gone after one drain.
    const s = summarisePlacement({
      pods: [pod({ cpu_request_m: 250, best_other_cpu_free_m: 72 })],
    });
    expect(isPinned(s.pinned[0])).toBe(true);
    expect(s.summary).toContain('pinned');
    expect(
      placementState(pod({ cpu_request_m: 250, best_other_cpu_free_m: 72 })),
    ).toBe('pinned');
  });

  it('a pod that could be placed again is not a problem', () => {
    const s = summarisePlacement({ pods: [pod()] });
    expect(s.pinned).toHaveLength(0);
    expect(s.refused).toHaveLength(0);
    expect(s.summary).toBe('every workload could be placed again');
    expect(placementState(pod())).toBe('fits');
  });

  it('a refused pod is never also counted as pinned', () => {
    // It is not placed, so there is no place it is holding. Counting it twice would inflate the
    // risk and make the page's numbers wrong in the direction that gets ignored.
    const s = summarisePlacement({
      pods: [pod({ unschedulable: true, best_other_cpu_free_m: 0 })],
    });
    expect(s.refused).toHaveLength(1);
    expect(s.pinned).toHaveLength(0);
  });
});

describe('the sentence that explains a full cluster that is idle', () => {
  it('names how much is reserved and unused, as a share of all requests', () => {
    const s = summarisePlacement({
      pods: [pod()],
      cpu_requested_m: 10468,
      cpu_used_m: 5379,
    });
    // Requests are reservations. A reservation nobody uses is a place no pod can have, and that
    // is the whole reason a cluster reads 96% full while running at 39%.
    expect(s.idleM).toBe(5089);
    expect(s.summary).toContain('5089m reserved but idle');
    expect(s.summary).toContain('49% of all requests');
  });

  it('does not invent an idle figure the receipt did not measure', () => {
    const s = summarisePlacement({ pods: [pod()], cpu_requested_m: 1000, cpu_used_m: null });
    expect(s.idleM).toBeNull();
    expect(s.summary).not.toContain('idle');
  });
});

describe('cells that must not flatter', () => {
  it('an unmeasured request is a dash, not zero', () => {
    expect(requestLabel(pod({ cpu_request_m: null }))).toBe('—');
    expect(requestLabel(pod({ cpu_request_m: 250 }))).toBe('250m');
  });

  it('an unmeasured headroom is a dash, so a pinned pod cannot look fine by accident', () => {
    // If headroom were rendered as 0 a pinned pod would be indistinguishable from one nobody
    // measured; if it were rendered as anything else the pod would look placeable.
    expect(headroomLabel(pod({ best_other_cpu_free_m: null }))).toBe('—');
    expect(headroomLabel(pod({ best_other_cpu_free_m: 72 }))).toBe('72m');
  });
});

describe('nothing has arrived yet', () => {
  it('is loading, not an empty and healthy cluster', () => {
    expect(summarisePlacement(null).state).toBe('loading');
    expect(summarisePlacement(null).summary).toBe('Reading placement…');
  });
});
