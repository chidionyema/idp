import { healthSentence, podNotReady, summarise } from './clusterHealth';

const node = (name: string, ready = 'True', unschedulable = false) => ({
  metadata: { name },
  spec: { unschedulable },
  status: { conditions: [{ type: 'Ready', status: ready }] },
});
const pod = (
  name: string,
  namespace: string,
  ready = 'True',
  phase = 'Running',
) => ({
  metadata: { name, namespace },
  status: { phase, conditions: [{ type: 'Ready', status: ready }] },
});
const flux = (
  name: string,
  ready = 'True',
  extra: Record<string, unknown> = {},
) => ({
  metadata: { name, namespace: 'flux-system' },
  status: {
    conditions: [
      {
        type: 'Ready',
        status: ready,
        reason:
          ready === 'True' ? 'ReconciliationSucceeded' : 'HealthCheckFailed',
      },
    ],
  },
  ...extra,
});

describe('summarise', () => {
  it('is good when every node, pod and Flux row is ready, and says the numbers', () => {
    const h = summarise(
      [node('a'), node('b')],
      [pod('p', 'x')],
      [flux('k')],
      [flux('h')],
      0,
    );
    expect(h.state).toBe('good');
    expect(healthSentence(h)).toBe(
      '2 of 2 nodes ready, 0 pods not ready, 2 of 2 Flux rows ready.',
    );
  });

  it('a node not ready outranks everything and names the node', () => {
    const h = summarise(
      [node('a'), node('b', 'False')],
      [],
      [flux('k', 'False')],
      [],
      0,
    );
    expect(h.state).toBe('red');
    expect(h.why).toBe('1 of 2 nodes not ready');
    expect(h.nodes.notReady).toEqual(['b']);
  });

  it('a cordoned node is not ready', () => {
    expect(
      summarise([node('a', 'True', true)], [], [], [], 0).nodes.ready,
    ).toBe(0);
  });

  it('counts pods not ready by namespace, largest first; finished pods do not count', () => {
    const h = summarise(
      [node('a')],
      [
        pod('p1', 'x', 'False'),
        pod('p2', 'y', 'False'),
        pod('p3', 'y', 'False'),
        pod('job', 'z', 'False', 'Succeeded'),
      ],
      [],
      [],
      0,
    );
    expect(h.podsNotReady).toEqual([
      { namespace: 'y', count: 2 },
      { namespace: 'x', count: 1 },
    ]);
    expect(h.state).toBe('red');
    expect(h.why).toBe('3 pods not ready');
    expect(podNotReady(pod('job', 'z', 'False', 'Succeeded'))).toBe(false);
  });

  it('lists every Flux row that is not ready with its kind and reason', () => {
    const h = summarise(
      [node('a')],
      [],
      [flux('k', 'False')],
      [flux('h', 'True', { spec: { suspend: true } })],
      0,
    );
    expect(h.flux).toMatchObject({ ready: 0, total: 2 });
    expect(h.flux.notReady.map(r => `${r.kind}/${r.name}:${r.state}`)).toEqual([
      'Kustomization/k:red',
      'HelmRelease/h:needs',
    ]);
    expect(h.state).toBe('red');
  });

  it('is blind, never green, when the cluster listed nothing', () => {
    expect(summarise([], [], [], [], 0).state).toBe('blind');
  });
});
