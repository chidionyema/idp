import {
  newsSince,
  parseLive,
  seenOf,
  type GreenlaneView,
} from './useGreenlaneLive';

const body = (over: Record<string, unknown> = {}) => ({
  available: true,
  lanes: [
    {
      name: 'lane/face-fix',
      status: 'testing',
      reason: '',
      attempts: 1,
      head: 'aaaa',
      age_min: 12,
    },
  ],
  batch: { id: 7, tip: 'ffff', lanes: ['lane/face-fix'], age_min: 9 },
  recent: [],
  landed: [{ lane: 'lane/old', batch: 5, waited_min: 30, ago_min: 40 }],
  timings: {
    queue_to_land_min: { n: 1, p50: 30, p90: 30 },
    batch_cycle_min: { n: 2, p50: 10, p90: 20 },
    outcomes: { 'green/landed': 1 },
  },
  sentence: 'Testing face-fix for 9 minutes.',
  read_at: '2026-10-20T10:00:00Z',
  ...over,
});

const view = (over: Record<string, unknown> = {}): GreenlaneView => {
  const r = parseLive(200, body(over));
  if (r.state !== 'ready') throw new Error('fixture did not parse');
  return r.view;
};

describe('parseLive', () => {
  it('reads a ready lane', () => {
    const v = view();
    expect(v.batch?.lanes).toEqual(['lane/face-fix']);
    expect(v.timings.queue_to_land_min.p50).toBe(30);
    expect(v.sentence).toBe('Testing face-fix for 9 minutes.');
  });
  it('an unreadable lane is unavailable with its reason, never an empty queue', () => {
    expect(
      parseLive(200, {
        available: false,
        error: 'the Greenlane state answered 401',
      }),
    ).toEqual({
      state: 'unavailable',
      error: 'the Greenlane state answered 401',
    });
    expect(parseLive(502, null)).toEqual({
      state: 'unavailable',
      error: 'greenlane/live answered 502',
    });
    expect(parseLive(200, { available: true })).toEqual({
      state: 'unavailable',
      error: 'greenlane/live sent no lane list',
    });
  });
  it('tolerates a backend that predates a field', () => {
    const r = parseLive(200, {
      available: true,
      lanes: [{ name: 'lane/x', status: 'pending' }, { bad: 1 }],
    });
    expect(r.state).toBe('ready');
    if (r.state !== 'ready') return;
    expect(r.view.lanes.map(l => l.name)).toEqual(['lane/x']);
    expect(r.view.batch).toBeNull();
    expect(r.view.timings.batch_cycle_min).toEqual({
      n: 0,
      p50: null,
      p90: null,
    });
  });
});

describe('newsSince', () => {
  it('the first poll is a baseline: nothing is said', () => {
    expect(newsSince(null, view())).toEqual([]);
  });
  it('says a new landing with its wait, and a new red with its reason but not its link', () => {
    const prev = seenOf(view());
    const next = view({
      lanes: [
        {
          name: 'lane/broken',
          status: 'red',
          reason:
            'ci failed: offline-gate https://github.com/x/y/actions/runs/1',
          attempts: 2,
          head: 'bbbb',
          age_min: 30,
        },
      ],
      landed: [
        { lane: 'lane/face-fix', batch: 7, waited_min: 14.6, ago_min: 0 },
        { lane: 'lane/old', batch: 5, waited_min: 30, ago_min: 41 },
      ],
    });
    expect(newsSince(prev, next)).toEqual([
      'face-fix landed after 15 minutes.',
      'broken is red: ci failed: offline-gate.',
    ]);
  });
  it('a lane already red is not said again', () => {
    const red = {
      name: 'lane/broken',
      status: 'red',
      reason: 'x',
      attempts: 1,
      head: 'b',
      age_min: 1,
    };
    const v = view({ lanes: [red] });
    expect(newsSince(seenOf(v), v)).toEqual([]);
  });
});
