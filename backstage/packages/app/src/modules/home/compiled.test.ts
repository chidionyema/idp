import { cpuLabel, guaranteed, millicores, summariseCompiled } from './compiled';
import type { CompiledDoc } from './compiled';

// `CompiledDoc['releases']` is optional, so it cannot be indexed directly. Naming the element
// type is clearer than the index expression and does not depend on the field being required.
type Release = NonNullable<CompiledDoc['releases']>[number];

const release = (over: Partial<Release> = {}) => ({
  namespace: 'observability',
  name: 'langfuse',
  chart: 'langfuse',
  version: '2.0.2',
  error: null,
  objects: [
    {
      kind: 'Deployment',
      namespace: 'observability',
      name: 'langfuse-web',
      resources: [
        { name: 'langfuse-web', requests: { cpu: '500m' }, limits: { cpu: '500m' } },
      ],
    },
  ],
  ...over,
});

const doc = (releases: unknown[]): CompiledDoc => ({
  releases: releases as CompiledDoc['releases'],
  summary: { total: releases.length, rendered: releases.length, failed: 0, objects: 1 },
});

describe('the compiled estate shows what the chart renders, never what a file claims', () => {
  it('reads the rendered cpu out of the document', () => {
    const s = summariseCompiled(doc([release()]));
    expect(s.workloads).toHaveLength(1);
    // 500m here is the RENDERED value. On 2026-09-12 the same workload rendered 1000m while the
    // comment beside the value claimed 500m, and the cluster ran 1000m. The page must show the
    // rendered number, because that is the one that will run.
    expect(cpuLabel(s.workloads[0].containers[0])).toBe('500m');
  });

  it('a chart that could not render is named, and the board says it is not ready', () => {
    const s = summariseCompiled(
      doc([release(), release({ name: 'weave-gitops', error: 'repo not found' })]),
    );
    // An unrendered chart is work whose numbers nobody knows. Counting it as fine is how eleven
    // blind charts went unnoticed when the compiler was first written.
    expect(s.unrendered).toHaveLength(1);
    expect(s.summary).toContain('could NOT be rendered');
    expect(s.summary).toContain('weave-gitops');
    expect(s.state).toBe('unavailable');
  });

  it('a document with no releases is unavailable, not empty', () => {
    // The estate has 31 HelmReleases. A document naming none is a broken compiler, and saying
    // "no releases" would hide that behind a calm empty state.
    const s = summariseCompiled({ releases: [], summary: { total: 0, rendered: 0 } });
    expect(s.state).toBe('unavailable');
  });

  it('nothing has arrived yet is loading', () => {
    expect(summariseCompiled(null).state).toBe('loading');
  });
});

describe('cells that must not flatter', () => {
  it('a container with no cpu request is a dash, not zero', () => {
    expect(cpuLabel({ name: 'x' })).toBe('—');
    expect(cpuLabel({ name: 'x', requests: { cpu: '50m' } })).toBe('50m');
  });

  it('request equal to limit is guaranteed, a split is not', () => {
    // Guaranteed QoS is what makes the kubelet evict this workload last; require-priority-class
    // refuses a split on the radio-room set, so a split shown here is a change admission would
    // reject rather than one that quietly took effect.
    expect(guaranteed({ requests: { cpu: '500m' }, limits: { cpu: '500m' } })).toBe(true);
    expect(guaranteed({ requests: { cpu: '250m' }, limits: { cpu: '1000m' } })).toBe(false);
    expect(guaranteed({ requests: { cpu: '500m' } })).toBe(false);
  });

  it('parses millicores and whole cores alike', () => {
    expect(millicores('500m')).toBe(500);
    expect(millicores('1')).toBe(1000);
    expect(millicores(undefined)).toBeNull();
    expect(millicores('')).toBeNull();
  });
});

describe('the count a person acts on', () => {
  it('counts workloads, not every rendered object', () => {
    const s = summariseCompiled(doc([release()]));
    expect(s.summary).toContain('1 workload');
    expect(s.summary).toContain('1 of 1 charts render');
  });

  it('does not claim a workload for an object with no containers', () => {
    const s = summariseCompiled(
      doc([
        release({
          objects: [
            { kind: 'Service', namespace: 'observability', name: 'langfuse-web', resources: [] },
          ],
        }),
      ]),
    );
    expect(s.workloads).toHaveLength(0);
  });
});
