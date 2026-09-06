import { act, fireEvent, screen, waitFor } from '@testing-library/react';
import {
  renderInTestApp,
  TestApiProvider,
  mockApis,
} from '@backstage/frontend-test-utils';
import { catalogApiRef } from '@backstage/plugin-catalog-react';
import { catalogApiMock } from '@backstage/plugin-catalog-react/testUtils';
import { configApiRef } from '@backstage/frontend-plugin-api';
import { kubernetesApiRef } from '@backstage/plugin-kubernetes';
import { Entity } from '@backstage/catalog-model';
import { EstateHome } from './EstateHome';
import { ago, count, fluxState, layerState, podsOf, verdict } from './estate';
import { REFRESH_MS, countInventory } from './useEstate';
import { screenUrl } from './estate';

const layer = (name: string, system = 'delivery'): Entity => ({
  apiVersion: 'backstage.io/v1alpha1',
  kind: 'Component',
  metadata: {
    name: `layer-${name}`,
    title: name,
    description: `The ${name} layer`,
    annotations: { 'estate/flux-kustomization': name },
  },
  spec: { type: 'platform-layer', system },
});
const door = (name: string, health?: string, at?: string): Entity => ({
  apiVersion: 'backstage.io/v1alpha1',
  kind: 'Component',
  metadata: {
    name,
    title: name,
    annotations: {
      ...(health ? { 'estate/health': health } : {}),
      ...(at ? { 'estate/health-checked-at': at } : {}),
    },
    links: [{ url: `https://${name}.example`, title: 'Open' }],
  },
  spec: { type: 'founder-surface' },
});
const system = (name: string, title: string): Entity => ({
  apiVersion: 'backstage.io/v1alpha1',
  kind: 'System',
  metadata: { name, title, description: `${title} in one sentence.` },
  spec: { owner: 'platform' },
});
const flux = (
  name: string,
  ready: 'True' | 'False' | 'Unknown',
  extra: any = {},
) => ({
  metadata: { name, namespace: 'flux-system' },
  ...extra,
  status: {
    conditions: [
      {
        type: 'Ready',
        status: ready,
        reason: ready === 'False' ? 'BuildFailed' : 'ReconciliationSucceeded',
      },
    ],
  },
});
const deployment = (layerName: string, ready: number, wanted: number) => ({
  metadata: {
    name: `${layerName}-d`,
    labels: { 'kustomize.toolkit.fluxcd.io/name': layerName },
  },
  spec: { replicas: wanted },
  status: { readyReplicas: ready },
});

const kubernetes = (
  items: { kustomizations?: any[]; deployments?: any[] } | Error,
) => ({
  getClusters: jest.fn(async () => [
    { name: 'estate', authProvider: 'serviceAccount' },
  ]),
  proxy: jest.fn(async ({ path }: { path: string }) => {
    if (items instanceof Error) throw items;
    const body = path.includes('kustomizations')
      ? items.kustomizations ?? []
      : items.deployments ?? [];
    return new Response(JSON.stringify({ items: body }), { status: 200 });
  }),
});

const render = (entities: Entity[], k8s: ReturnType<typeof kubernetes>) =>
  renderInTestApp(
    <TestApiProvider
      apis={[
        [catalogApiRef, catalogApiMock({ entities })],
        [
          configApiRef,
          mockApis.config({ data: { app: { title: 'Mumchimp estate' } } }),
        ],
        [kubernetesApiRef, k8s as any],
      ]}
    >
      <EstateHome />
    </TestApiProvider>,
  );

describe('estate logic', () => {
  it('turns Flux conditions into the six words, and never green for what it cannot see', () => {
    expect(fluxState(undefined).state).toBe('blind');
    expect(fluxState({ metadata: { name: 'x' } }).state).toBe('blind');
    expect(fluxState(flux('x', 'True')).state).toBe('good');
    expect(fluxState(flux('x', 'False')).state).toBe('red');
    expect(fluxState(flux('x', 'False')).why).toBe('BuildFailed');
    expect(fluxState(flux('x', 'Unknown')).state).toBe('running');
    expect(
      fluxState(flux('x', 'True', { spec: { suspend: true } })).state,
    ).toBe('needs');
  }, 15_000);
  it('reads pods through the label Flux stamps and reddens a ready layer with pods missing', () => {
    const d = [
      deployment('edge', 1, 3),
      deployment('edge', 2, 2),
      deployment('llm', 1, 1),
    ];
    expect(podsOf(d, 'edge')).toEqual({ ready: 3, wanted: 5 });
    expect(podsOf(d, 'nope')).toBeUndefined();
    const live = {
      kustomizations: { edge: flux('edge', 'True') },
      deployments: d,
      readAt: 0,
    };
    expect(layerState(layer('edge'), live)).toMatchObject({
      state: 'red',
      why: '3 of 5 pods ready',
    });
    expect(layerState(layer('edge'), undefined)).toMatchObject({
      state: 'blind',
    });
  }, 15_000);
  it('says the worst word first', () => {
    expect(verdict(count(['good', 'good']), 2)).toBe(
      'Everything we run is good. 2 services checked.',
    );
    expect(verdict(count(['good', 'red', 'red', 'needs']), 4)).toBe(
      '2 services are red.',
    );
    expect(verdict(count(['good', 'needs']), 2)).toBe('1 service needs you.');
    expect(verdict(count(['blind', 'good']), 2)).toBe(
      "1 service can't be checked.",
    );
    expect(verdict(count([]), 0)).toBe('Nothing is registered yet.');
  }, 15_000);
});

describe('age', () => {
  it('says how long a state has held, in the shortest true unit', () => {
    const now = Date.parse('2026-08-29T12:00:00Z');
    expect(ago('2026-08-29T11:59:40Z', now)).toBe('just now');
    expect(ago('2026-08-29T11:56:00Z', now)).toBe('4m ago');
    expect(ago('2026-08-29T09:00:00Z', now)).toBe('3h ago');
    expect(ago('2026-08-27T12:00:00Z', now)).toBe('2d ago');
    expect(ago('not a time', now)).toBeUndefined();
    expect(ago(undefined, now)).toBeUndefined();
  }, 15_000);
});

describe('EstateHome', () => {
  afterEach(() => {
    jest.useRealTimers();
    window.localStorage.clear();
  }, 15_000);

  it('shows how long each layer has held its state, from what Flux said', async () => {
    const k = flux('backstage', 'True');
    k.status.conditions[0].lastTransitionTime = new Date(
      Date.now() - 5 * 60_000,
    ).toISOString();
    await render(
      [system('delivery', 'Delivery'), layer('backstage')],
      kubernetes({ kustomizations: [k] }),
    );
    await waitFor(() =>
      expect(screen.getByTestId('age-layer-backstage')).toHaveTextContent(
        '5m ago',
      ),
    );
  }, 15_000);

  it('lands in the find box on / or Cmd+K from anywhere on the page', async () => {
    await render([layer('backstage')], kubernetes({}));
    const find = await screen.findByTestId('quick-find');
    (find as HTMLInputElement).blur();
    expect(find).not.toHaveFocus();
    fireEvent.keyDown(window, { key: '/' });
    expect(find).toHaveFocus();
    find.blur();
    fireEvent.keyDown(window, { key: 'k', metaKey: true });
    expect(find).toHaveFocus();
    // typing a slash inside a field is text, not a shortcut
    find.blur();
    fireEvent.keyDown(find, { key: '/' });
    expect(find).not.toHaveFocus();
  }, 15_000);

  it('keeps the board-or-list choice in the browser', async () => {
    await render(
      [system('delivery', 'Delivery'), layer('backstage')],
      kubernetes({ kustomizations: [flux('backstage', 'True')] }),
    );
    const list = await screen.findByTestId('view-list');
    expect(screen.getByTestId('view-board')).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    fireEvent.click(list);
    expect(list).toHaveAttribute('aria-pressed', 'true');
    expect(window.localStorage.getItem('estate.view')).toBe('list');
    expect(
      screen.getByTestId('system-delivery').querySelector('[data-view]'),
    ).toHaveAttribute('data-view', 'list');
  }, 15_000);

  it('re-reads the cluster every minute without asking the catalogue again', async () => {
    jest.useFakeTimers();
    const k8s = kubernetes({ kustomizations: [flux('backstage', 'True')] });
    await render([layer('backstage')], k8s);
    await screen.findByTestId('verdict');
    const before = k8s.proxy.mock.calls.length;
    expect(before).toBe(2);
    await act(async () => {
      jest.advanceTimersByTime(REFRESH_MS);
    });
    await waitFor(() => expect(k8s.proxy.mock.calls.length).toBe(before + 2));
  }, 15_000);

  it('shows every layer the cluster runs, grouped by system, with live state and pods', async () => {
    const now = new Date().toISOString();
    await render(
      [
        system('delivery', 'Delivery'),
        system('edge', 'Edge'),
        layer('backstage'),
        layer('kyverno', 'edge'),
        layer('dns', 'edge'),
        door('store', 'ok 200', now),
        door('grafana', 'FAIL 502', now),
      ],
      kubernetes({
        kustomizations: [flux('backstage', 'True'), flux('kyverno', 'False')],
        deployments: [deployment('backstage', 2, 2)],
      }),
    );
    await waitFor(() =>
      expect(screen.getByTestId('verdict')).toBeInTheDocument(),
    );
    // kyverno red, grafana down -> 2 red; dns missing from the cluster -> blind
    expect(screen.getByTestId('verdict')).toHaveTextContent(
      /2 of 5 services are failing right now/,
    );
    expect(screen.getByTestId('count-red')).toHaveTextContent('2');
    expect(screen.getByTestId('count-blind')).toHaveTextContent('1');
    expect(screen.getByTestId('count-good')).toHaveTextContent('2');
    // directive 1: the leading mark carries the worst present state, gradeable by data-state,
    // and its announcement is the same full verdict sentence (never a bare number beside a word).
    const dominant = screen.getByTestId('dominant');
    expect(dominant).toHaveAttribute('data-state', 'red');
    expect(dominant).toHaveTextContent(/2 of 5 services are failing right now/);
    // directive 2: the two red items are pulled into the top needs-your-hand band, each with
    // its own now-* id (so no tile id is duplicated), above the by-system bands.
    const bandNow = screen.getByTestId('band-now');
    expect(screen.getByTestId('now-layer-kyverno')).toHaveAttribute(
      'data-state',
      'red',
    );
    expect(screen.getByTestId('now-grafana')).toHaveAttribute(
      'data-state',
      'red',
    );
    // the actionable band is above the Everything band, not buried beneath it
    expect(bandNow.compareDocumentPosition(screen.getByTestId('band-everything')) &
      Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.getByTestId('system-delivery')).toHaveTextContent('Delivery');
    expect(screen.getByTestId('system-edge')).toHaveTextContent('Edge');
    expect(screen.getByTestId('layer-layer-kyverno')).toHaveAttribute(
      'data-state',
      'red',
    );
    expect(screen.getByTestId('layer-layer-dns')).toHaveAttribute(
      'data-state',
      'blind',
    );
    expect(screen.getByTestId('layer-layer-backstage')).toHaveTextContent(
      '2/2 pods',
    );
    expect(screen.getByTestId('surface-grafana')).toHaveAttribute(
      'data-state',
      'red',
    );
    expect(screen.getByTestId('health-store')).toHaveTextContent('Good');
    expect(screen.getByTestId('read-at')).toHaveTextContent('Live: read at');
    // the red counter is a filter
    fireEvent.click(screen.getByTestId('count-red'));
    expect(screen.queryByTestId('layer-layer-backstage')).toBeNull();
    expect(screen.getByTestId('layer-layer-kyverno')).toBeInTheDocument();
    expect(screen.queryByTestId('surface-store')).toBeNull();
    expect(screen.getByTestId('surface-grafana')).toBeInTheDocument();
    // no crew codes on the founder's surface
    expect(document.body.textContent).not.toMatch(/crew#|CP\d/);
  }, 15_000);

  it('puts the screens first, opens the ones with an address, greys the ones without', async () => {
    const now = new Date().toISOString();
    const screenDoor = (name: string, tags: string[], health?: string) => ({
      ...door(name, health, now),
      metadata: { ...door(name, health, now).metadata, tags },
    });
    await render(
      [
        layer('backstage'),
        screenDoor('traces', ['founder', 'screen'], 'ok 200'),
        screenDoor('dagster', ['founder', 'screen', 'no-address']),
        screenDoor('flux', ['founder', 'kubernetes', 'no-screen']),
        screenDoor('metrics', [
          'founder',
          'kubernetes',
          'screen',
          'no-address',
        ]),
        screenDoor('tailnet', ['founder', 'kubernetes', 'screen'], 'ok 200'),
        door('github', 'ok 200', now),
      ],
      kubernetes({ kustomizations: [flux('backstage', 'True')] }),
    );
    await waitFor(() =>
      expect(screen.getByTestId('verdict')).toBeInTheDocument(),
    );
    const band = screen.getByTestId('band-screens');
    expect(band).toBeInTheDocument();
    // screens come before the picture and the layers on the page
    expect(
      band.compareDocumentPosition(screen.getByTestId('band-layers')) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(screen.getByTestId('open-traces')).toHaveAttribute(
      'href',
      'https://traces.example',
    );
    expect(screen.getByTestId('open-traces')).toHaveTextContent('Open');
    expect(screen.getByTestId('screen-dagster')).toHaveAttribute(
      'data-state',
      'no-address',
    );
    expect(screen.queryByTestId('open-dagster')).toBeNull();
    expect(screen.getByTestId('health-dagster')).toHaveTextContent(
      'No address yet',
    );
    // the cluster tools sit in their own band, never in the screens strip
    const kube = screen.getByTestId('band-kubernetes');
    expect(kube).toHaveTextContent('Kubernetes tooling');
    expect(kube).toHaveTextContent('3');
    // directive 3: the three band-of-kind groups carry the same role, so the tag split reads as
    // one kind of thing (pages you open) rather than three unrelated bands.
    expect(band).toHaveTextContent('Pages you open');
    expect(kube).toHaveTextContent('Pages you open');
    expect(kube).toContainElement(screen.getByTestId('screen-flux'));
    expect(band).not.toContainElement(screen.getByTestId('screen-flux'));
    expect(screen.getByTestId('screen-flux')).toHaveAttribute(
      'data-state',
      'no-screen',
    );
    expect(screen.getByTestId('health-flux')).toHaveTextContent('No screen');
    expect(screen.queryByTestId('open-flux')).toBeNull();
    expect(screen.getByTestId('screen-metrics')).toHaveAttribute(
      'data-state',
      'no-address',
    );
    expect(screen.getByTestId('open-tailnet')).toHaveAttribute(
      'href',
      'https://tailnet.example',
    );
    // a plain door is still a door, not a screen
    expect(screen.queryByTestId('screen-github')).toBeNull();
    expect(screen.getByTestId('surface-github')).toBeInTheDocument();
    // directive 4: the door row carries live estate evidence of when it was last health-checked,
    // beyond a bare button; the github door was checked at fixture-now, so a recency line is on.
    expect(screen.getByTestId('health-github')).toBeInTheDocument();
    expect(screen.getByTestId('age-github')).toHaveTextContent(/^checked /);
    // the count of everything we hold, by what it is, and each chip lists them
    expect(screen.getByTestId('band-everything')).toHaveTextContent(
      'We hold 7 things.',
    );
    expect(
      screen.getByTestId('held-component-founder-surface'),
    ).toHaveTextContent('6');
    expect(
      screen.getByTestId('held-component-founder-surface'),
    ).toHaveTextContent('sign-in pages');
    expect(screen.getByTestId('held-component-platform-layer')).toHaveAttribute(
      'href',
      '/catalog?filters%5Bkind%5D=component&filters%5Btype%5D=platform-layer&filters%5Buser%5D=all',
    );
  }, 15_000);

  it('counts everything by kind and type, biggest first, and knows a screen address', () => {
    const rows = countInventory([
      layer('a'),
      layer('b'),
      door('x'),
      system('s', 'S'),
    ]);
    expect(rows.map(r => `${r.kind}/${r.type ?? ''}:${r.count}`)).toEqual([
      'Component/platform-layer:2',
      'Component/founder-surface:1',
      'System/:1',
    ]);
    expect(screenUrl(door('x'))).toBe('https://x.example');
    const dark = door('y');
    dark.metadata.tags = ['screen', 'no-address'];
    expect(screenUrl(dark)).toBeUndefined();
  });

  it('is blind, not green, when the cluster does not answer', async () => {
    await render(
      [layer('backstage'), door('store', 'ok 200', new Date().toISOString())],
      kubernetes(new Error('proxy 502')),
    );
    await waitFor(() =>
      expect(screen.getByTestId('verdict')).toBeInTheDocument(),
    );
    expect(screen.getByTestId('verdict')).toHaveTextContent(
      /1 of 2 services cannot be read at all/,
    );
    // nothing is red or needs-you here, so there is no needs-your-hand band to render
    expect(screen.queryByTestId('band-now')).toBeNull();
    expect(screen.getByTestId('read-at')).toHaveTextContent(
      'Not live: we could not reach the machines just now',
    );
    expect(screen.getByTestId('read-at')).toHaveAttribute(
      'title',
      'What the read said: proxy 502.',
    );
    expect(screen.getByTestId('layer-layer-backstage')).toHaveAttribute(
      'data-state',
      'blind',
    );
  }, 15_000);

  it('keeps the login drill contract when nothing is registered', async () => {
    await render([], kubernetes({}));
    await waitFor(() =>
      expect(screen.getByTestId('no-surfaces')).toBeInTheDocument(),
    );
    expect(screen.getByTestId('no-layers')).toBeInTheDocument();
    expect(screen.getByTestId('verdict')).toHaveTextContent(
      /We have nothing to show yet/,
    );
    // no actionable burden at all: the needs-your-hand band stays absent, not an empty shell
    expect(screen.queryByTestId('band-now')).toBeNull();
  }, 15_000);

  it('narrows by typing and stays honest about the catalogue failing', async () => {
    const now = new Date().toISOString();
    await render(
      [
        layer('backstage'),
        layer('kyverno', 'edge'),
        door('store', 'ok 200', now),
      ],
      kubernetes({
        kustomizations: [flux('backstage', 'True'), flux('kyverno', 'True')],
      }),
    );
    await waitFor(() =>
      expect(screen.getByTestId('quick-find')).toBeInTheDocument(),
    );
    fireEvent.change(screen.getByTestId('quick-find'), {
      target: { value: 'kyv' },
    });
    expect(screen.queryByTestId('layer-layer-backstage')).toBeNull();
    expect(screen.getByTestId('layer-layer-kyverno')).toBeInTheDocument();
    expect(screen.queryByTestId('surface-store')).toBeNull();
  }, 15_000);

  it('says the catalogue did not answer, and offers a retry', async () => {
    const failing = {
      getEntities: jest.fn().mockRejectedValue(new Error('catalog 503')),
    };
    await renderInTestApp(
      <TestApiProvider
        apis={[
          [catalogApiRef, failing as any],
          [configApiRef, mockApis.config()],
          [kubernetesApiRef, kubernetes({}) as any],
        ]}
      >
        <EstateHome />
      </TestApiProvider>,
    );
    await waitFor(() =>
      expect(screen.getByTestId('catalogue-error')).toBeInTheDocument(),
    );
    expect(screen.getByText('Try again')).toBeInTheDocument();
  }, 15_000);
});
