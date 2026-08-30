import { screen } from '@testing-library/react';
import {
  renderInTestApp,
  TestApiProvider,
  mockApis,
} from '@backstage/frontend-test-utils';
import { configApiRef } from '@backstage/frontend-plugin-api';
import { kubernetesApiRef } from '@backstage/plugin-kubernetes';
import { catalogApiRef } from '@backstage/plugin-catalog-react';
import { catalogApiMock } from '@backstage/plugin-catalog-react/testUtils';
import { Entity } from '@backstage/catalog-model';
import { Ops } from './Ops';
import { HELMRELEASES, KUSTOMIZATIONS, NODES, PODS } from './useClusterHealth';
import { ALERTS } from './useOpenReds';

const entities: Entity[] = [
  {
    apiVersion: 'backstage.io/v1alpha1',
    kind: 'Resource',
    metadata: {
      name: 'restore-drill',
      title: 'Restore drill',
      tags: ['never-run'],
    },
    spec: { type: 'drill', owner: 'group:default/platform' },
  },
  {
    apiVersion: 'backstage.io/v1alpha1',
    kind: 'Component',
    metadata: {
      name: 'signoz',
      title: 'SigNoz',
      annotations: {
        'estate/health': 'OK',
        'estate/health-checked-at': new Date().toISOString(),
      },
    },
    spec: { type: 'founder-surface', owner: 'group:default/watch' },
  },
];
const alerts = [
  {
    labels: { alertname: 'OttoDown', severity: 'critical' },
    annotations: { summary: 'Otto has no running pod' },
    startsAt: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
    status: { state: 'active' },
  },
];

const ready = (name: string, namespace: string, status = 'True') => ({
  metadata: { name, namespace },
  status: {
    phase: 'Running',
    conditions: [
      {
        type: 'Ready',
        status,
        reason: status === 'True' ? 'Ready' : 'HealthCheckFailed',
      },
    ],
  },
});

const render = (lists: Record<string, unknown[]>, fail = false) =>
  renderInTestApp(
    <TestApiProvider
      apis={[
        [
          kubernetesApiRef,
          {
            getClusters: async () => [{ name: 'estate' }],
            proxy: async ({ path }: { path: string }) =>
              fail
                ? { ok: false, status: 503, json: async () => ({}) }
                : {
                    ok: true,
                    status: 200,
                    json: async () =>
                      path === ALERTS ? alerts : { items: lists[path] ?? [] },
                  },
          } as any,
        ],
        [catalogApiRef, catalogApiMock({ entities })],
        [
          configApiRef,
          mockApis.config({ data: { app: { title: 'Mumchimp estate' } } }),
        ],
      ]}
    >
      <Ops />
    </TestApiProvider>,
  );

describe('Ops', () => {
  it('draws the cluster tile from the four list reads', async () => {
    await render({
      [NODES]: [ready('n1', ''), ready('n2', '')],
      [PODS]: [ready('p', 'a'), ready('q', 'b', 'False')],
      [KUSTOMIZATIONS]: [
        ready('platform', 'flux-system'),
        ready('edge', 'flux-system', 'False'),
      ],
      [HELMRELEASES]: [ready('signoz', 'observability')],
    });
    expect(await screen.findByTestId('ops-sentence')).toHaveTextContent(
      '2 of 2 nodes ready, 1 pods not ready, 2 of 3 Flux rows ready.',
    );
    expect(screen.getByTestId('ops-lead')).toHaveTextContent(
      'The cluster right now',
    );
    expect(screen.getByTestId('ops-cluster')).toHaveAttribute(
      'data-state',
      'red',
    );
    expect(screen.getByTestId('ops-flux')).toHaveTextContent('2 of 3');
    expect(screen.getByTestId('ops-cluster')).toHaveTextContent(
      'Kustomization flux-system/edge',
    );
    expect(screen.getByTestId('ops-cluster')).toHaveTextContent('b 1');
    expect(await screen.findByTestId('ops-reds-sentence')).toHaveTextContent(
      '2 reds open, 1 with no owner.',
    );
    const rows = screen.getAllByTestId('ops-red');
    expect(rows.map(r => r.getAttribute('data-kind'))).toEqual([
      'alert',
      'drill',
    ]);
    expect(rows[0]).toHaveTextContent('OttoDown');
    expect(rows[0]).toHaveTextContent('No owner');
    expect(rows[0]).toHaveTextContent('5m ago');
    expect(rows[0]).toHaveTextContent('No board link');
    expect(rows[1]).toHaveTextContent('Restore drill');
    expect(rows[1]).toHaveTextContent('platform');
    expect(rows[1]).toHaveTextContent('Run the drill and read its log');
  });

  it('says Alertmanager could not be read instead of zero reds', async () => {
    await render({}, true);
    expect(await screen.findByTestId('ops-reds-unread')).toHaveTextContent(
      'Alertmanager answered 503',
    );
    expect(screen.getByTestId('ops-reds-sentence')).toHaveTextContent(
      '1 red open, every one with an owner.',
    );
  });

  it('says the cluster could not be read instead of a green tile', async () => {
    await render({}, true);
    expect(await screen.findByTestId('ops-error')).toHaveTextContent(
      'answered 503',
    );
    expect(screen.queryByTestId('ops-cluster')).toBeNull();
  });
});
