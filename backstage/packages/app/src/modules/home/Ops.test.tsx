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
import { PLACEMENT_JSON } from './usePlacement';
import { COMPILED_JSON } from './useCompiled';
import { HELMRELEASES, KUSTOMIZATIONS, NODES, PODS } from './useClusterHealth';
import { ALERTS } from './useOpenReds';

// A guard inventory shaped exactly as mcp/plugins/estate_guards.py returns it: a total, a map of
// guards that FIRED, and anything that could not be read. Written with one guard that fired and
// one that refused, so the table is proved to carry both numbers.
const GUARDS = {
  total_guards: 56,
  fired: {
    'pre-commit': { fired: 249, blocked: 105, last_at: '2026-09-13T01:40:54Z', last_command: 'exit=1 event=git-hook' },
    'sleep-ban': { fired: 1, blocked: 1, last_at: '2026-09-13T00:01:41Z', last_command: 'sleep 420' },
  },
  unreadable: [],
};

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
                      url.endsWith('/guards')
                        ? GUARDS
                        : url.endsWith(HC_CHECKS)
                        ? healthchecks
                        : url.endsWith(INVENTORY_JSON)
                        ? inventory
                        : url.endsWith(PLACEMENT_JSON)
                        ? placement
                        : url.endsWith(COMPILED_JSON)
                        ? compiled
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

// The placement and compiled documents the page reads. Both answer as an honest empty state:
// a section whose source could not be read renders Unread, which is itself a behaviour under test.
const placement = {
  at: '2026-09-12T10:00:00Z',
  placement: { pods: [] },
  cpu_requested_m: 10468,
  cpu_used_m: 5379,
};
const compiled = {
  releases: [
    {
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
    },
  ],
  summary: { total: 1, rendered: 1, failed: 0, objects: 1 },
};

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
    expect(
      screen.getByText(/The cluster right now/),
    ).toBeInTheDocument();
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

describe('Ops — the guards section', () => {
  it('draws every guard that fired, with how many it refused', async () => {
    render({});
    expect(await screen.findByTestId('ops-guards-table')).toBeInTheDocument();
    // The guard that refused 105 times is on the page with its own number.
    // getAllByText: the guard's id appears in the row AND in the sentence above the table, and
    // getByText throws when a name is legitimately on the page twice.
    expect(screen.getAllByText('pre-commit').length).toBeGreaterThan(0);
    expect(screen.getByText('105')).toBeInTheDocument();
    // The page shows the guard's PLAIN-ENGLISH name, not its id -- a reader should not have to
    // know that `sleep-ban` means "Sleep ban". Both guards must appear, by the name a person reads.
    expect(screen.getAllByText('Sleep ban').length).toBeGreaterThan(0);
  });

  it('states how many guards exist, so a short table is not read as the whole estate', async () => {
    render({});
    const sentence = await screen.findByTestId('ops-guards-sentence');
    // 56 exist, 2 fired: the page must say both, or a reader sees 2 and concludes there are 2.
    expect(sentence).toHaveTextContent('56');
    expect(sentence).toHaveTextContent(/2 guards fired/);
  });

  it('says the guards could not be read instead of showing none', async () => {
    render({}, true);
    expect(await screen.findByTestId('ops-guards-error')).toBeInTheDocument();
    // The distinction this whole estate keeps getting wrong: no evidence is not a green tick.
    expect(screen.queryByTestId('ops-guards-table')).not.toBeInTheDocument();
  });
});
