import { screen, waitFor } from '@testing-library/react';

jest.setTimeout(60_000);
const SLOW = { timeout: 20_000 };
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
import { catalogApiRef } from '@backstage/plugin-catalog-react';
import { catalogApiMock } from '@backstage/plugin-catalog-react/testUtils';
import { kubernetesApiRef } from '@backstage/plugin-kubernetes';
import { Entity } from '@backstage/catalog-model';
import { Showcase } from './Showcase';
import { OTTO_INVENTORY_FILE, SHOWCASE_FILE } from './showcaseDocs';

const page = `- Entities: **582 ELITE**, **19 GAP**, **13 BLIND** of 614
- Standards rows: **11 live**, **12 not yet** of 23
`;
const inventory = `### Senses

- **Reads every Telegram message on one hardened door.** LIVE. \`platform/otto-gateway/deployment.yaml:22\`.
- **Hears voice notes.** IN THE IMAGE.

### Judgment and trust

- **Every tool call passes one gateway.** LIVE. \`otto/gateway/core.py:109\`.
`;

const layer = (name: string, system: string): Entity => ({
  apiVersion: 'backstage.io/v1alpha1',
  kind: 'Component',
  metadata: {
    name: `layer-${name}`,
    title: name,
    annotations: { 'estate/flux-kustomization': name },
  },
  spec: { type: 'platform-layer', system },
});
const system = (name: string, title: string): Entity => ({
  apiVersion: 'backstage.io/v1alpha1',
  kind: 'System',
  metadata: { name, title },
  spec: { owner: 'platform' },
});
const flux = (name: string, ready: 'True' | 'False') => ({
  metadata: { name, namespace: 'flux-system' },
  status: { conditions: [{ type: 'Ready', status: ready, reason: 'x' }] },
});

const kubernetes = {
  getClusters: jest.fn(async () => [{ name: 'estate', authProvider: 'serviceAccount' }]),
  proxy: jest.fn(async ({ path }: { path: string }) => {
    const body = path.includes('kustomizations')
      ? [flux('edge', 'True'), flux('otto', 'False')]
      : [];
    return new Response(JSON.stringify({ items: body }), { status: 200 });
  }),
};

const docs: Record<string, string> = {
  [SHOWCASE_FILE]: page,
  [OTTO_INVENTORY_FILE]: inventory,
};

const render = (missing: string[] = []) =>
  renderInTestApp(
    <TestApiProvider
      apis={[
        [
          catalogApiRef,
          catalogApiMock({
            entities: [
              layer('edge', 'edge'),
              layer('otto', 'agents'),
              system('edge', 'Edge'),
              system('agents', 'Agents'),
            ],
          }),
        ],
        [configApiRef, mockApis.config({ data: { app: { title: 'Estate' } } })],
        [kubernetesApiRef, kubernetes as any],
        [discoveryApiRef, { getBaseUrl: async () => 'http://backend/api/proxy' }],
        [
          fetchApiRef,
          {
            fetch: async (url: string) => {
              const file = Object.keys(docs).find(f => url.endsWith(f));
              const ok = Boolean(file) && !missing.includes(file!);
              return {
                ok,
                status: ok ? 200 : 404,
                json: async () => ({}),
                text: async () => (ok ? docs[file!] : ''),
              };
            },
          },
        ],
      ]}
    >
      <Showcase />
    </TestApiProvider>,
  );

describe('Showcase', () => {
  it('draws the grade, every system live, and the abilities Otto has today, from three reads', async () => {
    await render();
    await waitFor(() => expect(screen.getByTestId('showcase-facts')).toBeInTheDocument(), SLOW);
    expect(screen.getByTestId('showcase-elite')).toHaveTextContent('582');
    expect(screen.getByTestId('showcase-standards')).toHaveTextContent('11 of 23');
    await waitFor(() => expect(screen.getByTestId('showcase-picture')).toBeInTheDocument(), SLOW);
    expect(screen.getByTestId('showcase-systems-sentence')).toHaveTextContent('1 service is red');
    expect(screen.getByTestId('showcase-abilities').querySelectorAll('article, [data-testid^="ability-"]').length).toBeGreaterThan(0);
    expect(screen.getByTestId('ability-0')).toHaveTextContent('Reads every Telegram message');
    expect(screen.getByTestId('ability-1')).toHaveTextContent('otto/gateway/core.py:109');
    expect(screen.queryByText(/Hears voice notes/)).not.toBeInTheDocument();
    expect(screen.getByTestId('showcase-otto-sentence')).toHaveTextContent('2 abilities');
  });
  it('says plainly which document could not be read and keeps the other standing', async () => {
    await render([SHOWCASE_FILE]);
    await waitFor(() => expect(screen.getByTestId('showcase-bar-error')).toBeInTheDocument(), SLOW);
    expect(screen.getByTestId('showcase-bar-error')).toHaveTextContent('404');
    expect(screen.getByTestId('ability-0')).toBeInTheDocument();
  });
});
