// The graph section's behaviour, graded on the three states rather than on wording.
//
// Each case below is a state the estate can genuinely be in, taken from the real graph on
// 2026-09-12 (store/catalog/estate.db, 648 stranded branches, 21 dead pods, 45 k8sgpt
// findings). The assertions are on WHICH state is reported and WHAT leads the sentence --
// never on a phrase that a copy edit would break.
import { ago, domainRows, EstateGraph, graphSentence, worst } from './estateGraph';

const graph = (over: Partial<EstateGraph> = {}): EstateGraph => ({
  read_at: '2026-09-12 11:24:42',
  domains: [
    { domain: 'code', state: 'MEASURED_FAIL', nodes: 649, not_serving: 648, age_s: 12, window_s: 180 },
    { domain: 'runtime', state: 'MEASURED_FAIL', nodes: 855, not_serving: 410, age_s: 12, window_s: 180 },
  ],
  counts: [],
  not_serving_total: 1058,
  not_serving: [
    { id: 'k8s:deployment:commerce:lago-api', status: 'dead', detail: { namespace: 'commerce', ready: 0, replicas: 1 } },
    { id: 'k8s:pod:commerce:lago-api-5686d85ff7-zxr26', status: 'crashlooping', detail: { restarts: 6 } },
  ],
  evidence: [{ type: 'event', n: 240 }],
  truncated: false,
  ...over,
});

describe('ago', () => {
  it('reads seconds as a person would', () => {
    expect(ago(12)).toBe('12s ago');
    expect(ago(600)).toBe('10m ago');
    expect(ago(7200)).toBe('2h ago');
    expect(ago(172800)).toBe('2d ago');
  });

  it('says never when there is no reading at all, rather than zero', () => {
    // A null age is "never read", not "read at epoch". Rendering it as a number would make
    // the worst possible state look like the freshest.
    expect(ago(null)).toBe('never');
  });
});

describe('graphSentence', () => {
  it('leads with the unknown domain when one is stale, not with the count', () => {
    const stale = graph({
      domains: [{ domain: 'runtime', state: 'UNKNOWN', nodes: 855, age_s: 86400, window_s: 180 }],
    });
    const s = graphSentence(stale);
    expect(s).toContain('runtime');
    expect(s).toContain('memory, not a reading');
  });

  it('reports failing domains by name and count', () => {
    const s = graphSentence(graph());
    expect(s).toContain('code');
    expect(s).toContain('runtime');
    expect(s).toContain('648');
  });

  it('says so plainly when nothing is unserved', () => {
    const clean = graph({
      domains: [{ domain: 'runtime', state: 'MEASURED_OK', nodes: 10, not_serving: 0, age_s: 5, window_s: 180 }],
      not_serving: [],
      not_serving_total: 0,
    });
    expect(graphSentence(clean)).not.toContain('not serving');
  });

  it('names the reason when the graph does not exist at all', () => {
    // BLIND, not clean. An absent graph rendered as "nothing is unserved" is the exact lie
    // this whole system was built to end.
    const absent = graph({ why: 'the estate graph is not at /data/estate.db', domains: [] });
    expect(graphSentence(absent)).toContain('/data/estate.db');
  });
});

describe('domainRows', () => {
  it('never reports a stale domain as serving', () => {
    const rows = domainRows(
      graph({ domains: [{ domain: 'runtime', state: 'UNKNOWN', nodes: 855, age_s: 99999, window_s: 180 }] }),
    );
    expect(rows[0].state).toBe('UNKNOWN');
    expect(rows[0].detail).not.toContain('not serving');
    expect(rows[0].detail).toContain('window');
  });

  it('carries the split for a failing domain', () => {
    const rows = domainRows(graph());
    expect(rows.find(r => r.domain === 'code')?.detail).toContain('648 of 649');
  });
});

describe('worst', () => {
  it('keeps the tool’s own ordering, which puts workloads before pods', () => {
    // The tool orders deployment > statefulset > daemonset > pod. A UI that re-sorted would
    // bury the dead deployment under 240 warning events, the same mistake the first dead
    // list made at 215 rows.
    expect(worst(graph())[0].id).toContain('deployment');
  });

  it('shows at most what it was asked for', () => {
    const many = graph({
      not_serving: Array.from({ length: 50 }, (_, i) => ({
        id: `k8s:pod:ns:p${i}`,
        status: 'dead',
        detail: {},
      })),
    });
    expect(worst(many, 8)).toHaveLength(8);
  });
});
