// These tests grade the "On the cluster" live card on the estate entity overview: for a layer
// that genuinely sits on the cluster, a person reads whether it is Ready and how many pods are
// up, in words, and is never told "fine" when nothing could be read. The pure sentence helper
// is graded with fixtures; the rendered card is graded with a faked cluster behind the
// Kubernetes API the portal already uses. No layout words, no selectors (R53).
import { renderInTestApp, TestApiProvider } from '@backstage/frontend-test-utils';
import { kubernetesApiRef } from '@backstage/plugin-kubernetes';
import { Entity } from '@backstage/catalog-model';
import { screen } from '@testing-library/react';
import { LayerOnCluster, layerSentence, layerStateLine } from './live';
import type { LayerState } from '../home/estate';

// A platform layer the estate catalogue generator stamps: it carries the flux kustomization
// annotation (estate/flux-kustomization -> the flux name) that every shipped layer has.
const layer = (name = 'alerts', flux = 'alerts'): Entity => ({
  apiVersion: 'backstage.io/v1alpha1',
  kind: 'Component',
  metadata: {
    name: `layer-${name}`,
    namespace: 'default',
    title: `${name} layer`,
    annotations: { 'estate/flux-kustomization': flux },
  },
  spec: { type: 'platform-layer' },
});

const READY: LayerState = {
  state: 'good',
  why: 'Ready',
  pods: { ready: 2, wanted: 2 },
};
const FAILED: LayerState = {
  state: 'red',
  why: 'ApplyFailed',
  pods: { ready: 0, wanted: 2 },
};
const BLIND: LayerState = {
  state: 'blind',
  why: 'The cluster did not answer',
};

describe('layerSentence (pure)', () => {
  it('says a ready layer is ready and names the pods, in words a stranger reads', () => {
    const s = layerSentence(READY);
    expect(s).toMatch(/Ready/);
    expect(s).toMatch(/2 of 2/);
  });

  it('says a failed layer gives the why, never a bare github link and never claims Ready', () => {
    const s = layerSentence(FAILED);
    expect(s).toMatch(/ApplyFailed/);
    expect(s).not.toMatch(/github\.com/);
    expect(s).not.toMatch(/^Ready| Ready/);
  });

  it('a layer that could not be read is told so in words, never a silent green', () => {
    // The card's unread path renders layerStateLine({state:'unread'}) -> why 'The cluster did
    // not answer'; grade that sentence, not a made-up fixture word.
    const viaUnread = layerSentence(
      layerStateLine({ state: 'unread', error: '404' } as never),
    );
    expect(viaUnread).toMatch(/cluster did not answer/i);
    expect(viaUnread).not.toMatch(/ready|up|ok|fine|green/i);
    // The BLIND fixture (no pods, cluster silent) must not read green either.
    const s = layerSentence(BLIND);
    expect(s).not.toMatch(/^Ready| Ready|green|fine/);
  });

  it('turns a loading read into a Reading line, not a verdict', () => {
    const st = layerStateLine({ state: 'loading' } as never);
    expect(layerSentence(st)).toMatch(/Reading/i);
  });
  it('a layer with no live cluster verdict is not shown as a bare count of fictional pods', () => {
    // A handful-of-nothing bug would render pods for a blind layer; the card must not.
    expect(layerSentence(BLIND)).not.toMatch(/of .* pods/);
  });
});

// A faked Kubernetes API behind kubernetesApiRef: serves the two /apis endpoints the card's
// hook reads, returning a ready or failing layer's objects.
const fakeCluster = (flux: string, ready: boolean) => ({
  getClusters: async () => [{ name: 'estate' }],
  proxy: async ({ path }: { path: string }) => {
    const byPath: Record<string, unknown> = {
      '/apis/kustomize.toolkit.fluxcd.io/v1/kustomizations': {
        items: [
          {
            metadata: { name: flux },
            status: {
              conditions: [
                ready
                  ? { type: 'Ready', status: 'True', reason: 'ReconciliationSucceeded' }
                  : { type: 'Ready', status: 'False', reason: 'ApplyFailed' },
              ],
            },
          },
        ],
      },
      '/apis/apps/v1/deployments': {
        items: ready
          ? [
              {
                metadata: {
                  name: `${flux}-x`,
                  labels: { 'kustomize.toolkit.fluxcd.io/name': flux },
                },
                spec: { replicas: 2 },
                status: { readyReplicas: 2, replicas: 2 },
              },
            ]
          : [],
      },
    };
    const body = byPath[path];
    if (!body) return { ok: false, status: 404, json: async () => ({}) } as Response;
    return { ok: true, status: 200, json: async () => body } as unknown as Response;
  },
});

describe('LayerOnCluster (rendered behind kubernetesApiRef)', () => {
  it('renders a ready layer as Ready with its pod count from the live cluster read', async () => {
    await renderInTestApp(
      <TestApiProvider apis={[[kubernetesApiRef, fakeCluster('alerts', true) as never]]}>
        <LayerOnCluster entity={layer('alerts', 'alerts')} />
      </TestApiProvider>,
    );
    expect(await screen.findByTestId('layer-on-cluster')).toBeInTheDocument();
    expect(await screen.findByText(/2 of 2 pods ready/i)).toBeInTheDocument();
    expect(screen.getAllByText(/On the cluster/i).length).toBeGreaterThan(0);
  });

  it('renders a failing layer as not ready with the Flux reason, no green', async () => {
    await renderInTestApp(
      <TestApiProvider apis={[[kubernetesApiRef, fakeCluster('alerts', false) as never]]}>
        <LayerOnCluster entity={layer('alerts', 'alerts')} />
      </TestApiProvider>,
    );
    expect(await screen.findByText(/ApplyFailed/i)).toBeInTheDocument();
  });
});
