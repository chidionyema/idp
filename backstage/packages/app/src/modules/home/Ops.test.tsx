import { screen } from '@testing-library/react';
import {
  renderInTestApp,
  TestApiProvider,
  mockApis,
} from '@backstage/frontend-test-utils';
import { configApiRef } from '@backstage/frontend-plugin-api';
import { kubernetesApiRef } from '@backstage/plugin-kubernetes';
import { Ops } from './Ops';
import { HELMRELEASES, KUSTOMIZATIONS, NODES, PODS } from './useClusterHealth';

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
                    json: async () => ({ items: lists[path] ?? [] }),
                  },
          } as any,
        ],
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
  });

  it('says the cluster could not be read instead of a green tile', async () => {
    await render({}, true);
    expect(await screen.findByTestId('ops-error')).toHaveTextContent(
      'answered 503',
    );
    expect(screen.queryByTestId('ops-cluster')).toBeNull();
  });
});
