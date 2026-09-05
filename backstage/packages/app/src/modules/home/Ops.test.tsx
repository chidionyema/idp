import { screen } from '@testing-library/react';
import {
  renderInTestApp,
  TestApiProvider,
  mockApis,
} from '@backstage/frontend-test-utils';
import {
  configApiRef,
  discoveryApiRef,
  fetchApiRef,
} from '@backstage/frontend-plugin-api';
import { kubernetesApiRef } from '@backstage/plugin-kubernetes';
import { catalogApiRef } from '@backstage/plugin-catalog-react';
import { catalogApiMock } from '@backstage/plugin-catalog-react/testUtils';
import { Entity } from '@backstage/catalog-model';
import { HC_CHECKS } from './healthchecks';
import { INVENTORY_JSON } from './inventory';
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

const founder = {
  taken: '2026-08-30T03:00Z',
  waiting: [
    {
      issue: 693,
      url: 'https://github.com/chidionyema/crew/issues/693',
      cp: 'CP1',
      what: 'Founder replies APPROVE: crew#693',
    },
  ],
  receipts: [
    {
      repo: 'chidionyema/idp',
      number: 918,
      title: 'Ops page',
      url: 'https://github.com/chidionyema/idp/pull/918',
      merged_at: new Date(Date.now() - 20 * 60_000).toISOString(),
      use: 'open the portal, sidebar Ops',
    },
  ],
};

const healthchecks = {
  checks: [
    { name: 'estate-render', status: 'up' },
    { name: 'science-collect', status: 'down' },
  ],
};

const inventory = {
  generated_at: new Date(Date.now() - 3 * 60 * 60_000).toISOString(),
  counts: {
    mac: {
      MANAGED: 44,
      DRIFTED: 0,
      ORPHAN: 6,
      GHOST: 0,
      UNKNOWN: false,
      read: 'yes',
    },
    github: {
      MANAGED: 0,
      DRIFTED: 0,
      ORPHAN: 0,
      GHOST: 0,
      UNKNOWN: true,
      read: 'UNKNOWN',
    },
  },
  blind: ['github: steampipe is not installed'],
  rows: [],
};

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
          discoveryApiRef,
          { getBaseUrl: async () => 'http://backend/api/proxy' },
        ],
        [
          fetchApiRef,
          {
            fetch: async (url: string) =>
              fail
                ? { ok: false, status: 502, json: async () => ({}) }
                : {
                    ok: true,
                    status: 200,
                    json: async () =>
                      url.endsWith(HC_CHECKS)
                        ? healthchecks
                        : url.endsWith(INVENTORY_JSON)
                        ? inventory
                        : founder,
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

  it('draws the founder tiles from founder.json through the proxy', async () => {
    await render({});
    expect(await screen.findByTestId('ops-waiting-sentence')).toHaveTextContent(
      '1 checkpoint waits on you.',
    );
    expect(
      screen
        .getByTestId('ops-waiting-row')
        .textContent?.replace('Opens in a new window', ''),
    ).toMatch(/crew#693 CP1,?\s+Founder replies APPROVE: crew#693/);
    expect(screen.getByTestId('ops-receipts-sentence')).toHaveTextContent(
      '1 receipt, newest first.',
    );
    expect(
      screen
        .getByTestId('ops-receipt-row')
        .textContent?.replace('Opens in a new window', ''),
    ).toMatch(/idp#918,?\s+open the portal, sidebar Ops 20m ago/);
  });

  it('says what waits on the founder is unknown when founder.json cannot be read', async () => {
    await render({}, true);
    expect(await screen.findByTestId('ops-founder-error')).toHaveTextContent(
      'answered 502',
    );
    expect(screen.queryByTestId('ops-waiting')).toBeNull();
  });

  it('draws the drills row and the scheduled-jobs tile (crew#684 CP5)', async () => {
    await render({});
    expect(await screen.findByTestId('ops-drills-sentence')).toHaveTextContent(
      /of \d+ drills green/,
    );
    expect(
      await screen.findByTestId('ops-healthchecks-sentence'),
    ).toHaveTextContent('1 of 2 up, 1 down.');
    expect(screen.getByTestId('ops-healthcheck-row')).toHaveTextContent(
      'science-collect Down',
    );
  });

  it('says scheduled jobs are unknown when Healthchecks cannot be read', async () => {
    await render({}, true);
    expect(
      await screen.findByTestId('ops-healthchecks-error'),
    ).toHaveTextContent('answered 502');
    expect(screen.queryByTestId('ops-healthchecks')).toBeNull();
  });

  it('draws the estate inventory tile from inventory.json on the state branch (crew#740)', async () => {
    await render({});
    expect(
      await screen.findByTestId('ops-inventory-sentence'),
    ).toHaveTextContent('6 things not as git says; 1 plane could not be read.');
    const rows = screen.getAllByTestId('ops-inventory-row');
    expect(rows.map(r => r.getAttribute('data-read'))).toEqual([
      'UNKNOWN',
      'yes',
    ]);
    expect(rows[0]).toHaveTextContent(
      'GitHub: could not be read, so what it holds is unknown',
    );
    expect(rows[1]).toHaveTextContent('Mac: 44 managed, 6 orphans');
    expect(screen.getByTestId('ops-inventory-blind')).toHaveTextContent(
      'steampipe is not installed',
    );
    expect(screen.getByTestId('ops-inventory')).toHaveTextContent('3h ago');
    expect(screen.getByTestId('ops-inventory')).toHaveTextContent(
      'The full table',
    );
  });

  it('says the inventory is unknown when inventory.json cannot be read', async () => {
    await render({}, true);
    expect(await screen.findByTestId('ops-inventory-error')).toHaveTextContent(
      'answered 502',
    );
    expect(screen.queryByTestId('ops-inventory')).toBeNull();
  });
});
