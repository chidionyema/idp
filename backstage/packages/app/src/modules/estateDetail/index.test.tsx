// These tests grade what a person reads on the estate entity overview tab (founder,
// "clicking needs more detail and overview"): the estate facts bin/catalog-gen wrote on the
// entity, its category membership, and that a linked relation takes a person deeper into the
// catalogue instead of leaving it. No layout words, no selectors (R53); visible text finds it.
import { renderInTestApp, TestApiProvider } from '@backstage/frontend-test-utils';
import { catalogApiRef } from '@backstage/plugin-catalog-react';
import { EntityProvider } from '@backstage/plugin-catalog-react';
import { Entity } from '@backstage/catalog-model';
import { screen } from '@testing-library/react';
import { EstateOverview } from './index';

const NOW = Date.parse('2026-08-29T12:00:00Z');

/** A home-routed founder-surface that the estate health poller genuinely reaches: it carries
 * the live health verdict + checked-at annotations the home DoorRow reads (estate/health,
 * estate/health-checked-at) but NO generated estate/<fact> block (a hand-authored component).
 * Removing the old `isEstateGenerated` gate must not leave this a dead stub. */
const founderSurface = ({
  health = 'ok 200',
  checkedAt = '2026-08-29T11:56:00Z',
}: {
  health?: string;
  checkedAt?: string;
} = {}): Entity => ({
  apiVersion: 'backstage.io/v1alpha1',
  kind: 'Component',
  metadata: {
    name: 'founder-console',
    namespace: 'default',
    title: 'Founder console',
    description: 'The sign-in page founders reach first.',
    annotations: {
      'estate/health': health,
      'estate/health-checked-at': checkedAt,
      'github.com/project-slug': 'example/founder-console',
    },
    tags: ['founder'],
    links: [
      { url: 'https://github.com/example/founder-console', title: 'Source' },
    ],
  },
  spec: { type: 'founder-surface', owner: 'group:default/platform' },
});

/** A founder-surface the probe has NOT yet reached: it carries only the well-known backstage
 * keys (no estate/health / no estate/health-checked-at, as in the library / non-probe catalogue
 * render). Stone-2: the authored overview still belongs to it (owner, system, links) without
 * any fabricated live claim. */
const unprobedSurface = (): Entity => ({
  apiVersion: 'backstage.io/v1alpha1',
  kind: 'Component',
  metadata: {
    name: 'founder-inbox',
    namespace: 'default',
    title: 'Founder inbox',
    description: "Where the day's decisions land.",
    annotations: { 'github.com/project-slug': 'example/founder-inbox' },
    tags: ['founder'],
    links: [{ url: 'https://example.com/inbox', title: 'Open inbox' }],
  },
  spec: {
    type: 'founder-surface',
    system: 'system:default/product-estate',
    owner: 'group:default/platform',
  },
});

/** A generated estate ledger row, as bin/catalog-gen writes it (in the estate-internals
 * system after the de-noise change: estate/* annotations present, estate-internal tag). */
const generatedLedger = (): Entity => ({
  apiVersion: 'backstage.io/v1alpha1',
  kind: 'Resource',
  metadata: {
    name: 'claude-state-prompt-ledger-dev-example',
    namespace: 'default',
    title: 'A prompt ledger',
    description: 'Per-session Claude prompt ledger.',
    annotations: {
      'estate/kind': 'ledger',
      'estate/rows': '42',
      'estate/mb': '2',
      'estate/coupling': 'anthropic',
      'estate/path': '~/.claude/state/prompt-ledger/example',
    },
    tags: ['ledger', 'estate-internal'],
    links: [
      { url: 'https://github.com/example/estate', title: 'Source' },
      { url: 'https://example.com/ledger', title: 'Open ledger' },
    ],
  },
  spec: { type: 'ledger', system: 'system:default/estate-internals', owner: 'group:default/platform' },
});

/** A catalogue entry a person might click that is NOT estate-generated (a hand-authored
 * component with only well-known keys): it should still render its name and description, but
 * no estate/* fact is claimed on it. */
const handAuthored = (): Entity => ({
  apiVersion: 'backstage.io/v1alpha1',
  kind: 'Component',
  metadata: {
    name: 'dashboard',
    namespace: 'default',
    title: 'The dashboard',
    description: 'A component we wrote by hand.',
    annotations: { 'github.com/project-slug': 'example/dashboard' },
    tags: ['frontend'],
  },
  spec: { type: 'service', owner: 'group:default/platform' },
});

/** Entities the card's relation read can resolve, keyed by entityRef. Tests that assert a
 * real neighbour set one up; the default (no neighbours) keeps the assertions about honesty
 * (a surface nobody references states that plainly, never a fabricated wire). */
let neighbours: Record<string, Entity> = {};

/** A catalog service that answers relation refs the way the live catalogue does: getEntitiesByRefs
 * returns the keyed neighbours and null for anything not present. */
const catalogStub = () => ({
  getEntitiesByRefs: async ({ entityRefs }: { entityRefs: string[] }) => ({
    items: entityRefs.map(ref => neighbours[ref] ?? null),
  }),
  getEntities: async () => ({ items: [] as Entity[] }),
});

const renderOne = (entity: Entity, now: number = Date.now()) => {
  const api = catalogStub();
  return renderInTestApp(
    <TestApiProvider apis={[[catalogApiRef, api as any]]}>
      <EntityProvider entity={entity}>
        <EstateOverview now={now} />
      </EntityProvider>
    </TestApiProvider>,
  );
};

describe('EstateOverview (the owned estate entity detail tab)', () => {
  beforeEach(() => {
    neighbours = {};
  });

  it('renders the title and the generated estate facts', async () => {
    await renderOne(generatedLedger());
    // The owner of the page.
    expect(screen.getByText('A prompt ledger')).toBeInTheDocument();
    // fact values catalog-gen annotated on the row: rows and coupling are shown.
    expect(screen.getByText('42')).toBeInTheDocument();          // estate/rows
    expect(screen.getByText('anthropic')).toBeInTheDocument();   // estate/coupling
  });

  it('shows which category the entity belongs to and links deeper, not away', async () => {
    await renderOne(generatedLedger());
    // The estate-internals System it belongs to is reachable inside the catalogue.
    const systemLink: HTMLElement = screen.getByText('estate-internals').closest('a')!;
    expect(systemLink.getAttribute('href')).toMatch(/^\/catalog\/system\//);
    // Its Non-GitHub "Open ledger" destination appears, not only a GitHub Source tile
    // (directive: 26 of 116 components carry only GitHub links; an estate destination is
    // shown here).
    expect(screen.getByText('Open ledger')).toBeInTheDocument();
  });

  it("authors a plain service component's click-through without inventing an estate fact", async () => {
    await renderOne(handAuthored());
    expect(screen.getByText('The dashboard')).toBeInTheDocument();
    // No estate/ fact block is rendered because there were none generated for it.
    expect(screen.queryByText('Rows')).not.toBeInTheDocument();
    expect(screen.queryByText('Coupling')).not.toBeInTheDocument();
    // The owned overview names who owns it (its group), so a click is not a stock stub.
    expect(screen.getByText(/Owner/)).toBeInTheDocument();
    expect(screen.getByText('platform').closest('a')?.getAttribute('href')).toMatch(
      /^\/catalog\/group\//,
    );
  });

  it('turns a home founder-surface click into a live overview, not a stub (founder note: clicking needs more detail)', async () => {
    // A hand-authored founder-surface carries the poller's live health verdict + checked time
    // but no generated estate/<fact> block. The estate speaks about it rather than stock stub.
    await renderOne(founderSurface({ checkedAt: '2026-08-29T11:56:00Z' }), NOW);
    expect(screen.getByText('Founder console')).toBeInTheDocument();
    // It is running, and the last health check is recent and dated on the page.
    expect(screen.getByText('Up')).toBeInTheDocument();
    expect(screen.getByText(/checked 4m ago/)).toBeInTheDocument();
    // No generated fact is invented for a hand-authored entry (there were none to claim).
    expect(screen.queryByText('Rows')).not.toBeInTheDocument();
  });

  it('says plainly, in the same words as the home row, that a down surface is down', async () => {
    await renderOne(
      founderSurface({
        health: 'FAIL 502 from http://example.invalid/healthz',
        checkedAt: '2026-08-29T11:59:00Z',
      }),
      NOW,
    );
    // Same state vocabulary the home hero uses (Down), not a colour or a bare icon.
    expect(screen.getByText('Down')).toBeInTheDocument();
    expect(screen.queryByText('Up')).not.toBeInTheDocument();
  });

  it('claims no live state for a surface the estate has never health-checked', async () => {
    // The poller has not reached it (no estate/health); nothing live may be asserted (rule 13).
    await renderOne(
      {
        ...founderSurface({}),
        metadata: {
          ...founderSurface({}).metadata,
          annotations: { 'github.com/project-slug': 'example/founder-console' },
        },
      },
      NOW,
    );
    expect(screen.getByText('Founder console')).toBeInTheDocument();
    expect(screen.queryByText('Down')).not.toBeInTheDocument();
    expect(screen.queryByText('Up')).not.toBeInTheDocument();
    expect(screen.queryByText(/checked /)).not.toBeInTheDocument();
  });

  it('gives an unprobed founder-surface an authored overview, with no invented live claim', async () => {
    // Stone 2: a surface the probe has not yet stamped (library / non-probe catalogue render)
    // must still not be a stock stub - the estate authors who owns it and what system it serves.
    await renderOne(unprobedSurface());
    expect(screen.getByText('Founder inbox')).toBeInTheDocument();
    expect(screen.getByText(/Owner/)).toBeInTheDocument();
    expect(screen.getByText('product-estate').closest('a')?.getAttribute('href')).toMatch(
      /^\/catalog\/system\//,
    );
    // It is NOT probed, so no live Up/Down/checked may be claimed (rule 13).
    expect(screen.queryByText('Up')).not.toBeInTheDocument();
    expect(screen.queryByText('Down')).not.toBeInTheDocument();
    expect(screen.queryByText(/checked /)).not.toBeInTheDocument();
  });

  it("reads what a component depends on from its real catalogue relations, not a guessed list", async () => {
    // `spec.dependsOn`-style outbound relation: this component names a real catalogue member
    // it talks to, and the estate resolves it to an in-portal deep link.
    neighbours['component:default/heartbeat'] = {
      apiVersion: 'backstage.io/v1alpha1',
      kind: 'Component',
      metadata: { name: 'heartbeat', namespace: 'default', title: 'Heartbeat' },
      spec: { type: 'platform-layer' },
    };
    const host: Entity = {
      apiVersion: 'backstage.io/v1alpha1',
      kind: 'Component',
      metadata: {
        name: 'founder-inbox',
        namespace: 'default',
        title: 'Founder inbox',
        description: "Where the day's decisions land.",
      },
      relations: [
        {
          type: 'dependsOn',
          targetRef: 'component:default/heartbeat',
        },
      ],
      spec: { type: 'founder-surface', owner: 'group:default/platform' },
    };
    await renderOne(host);
    await screen.findByText('Heartbeat - platform-layer');
    expect(screen.getByText('What it talks to')).toBeInTheDocument();
    expect(screen.getByText('It depends on')).toBeInTheDocument();
    expect(screen.getByText('Heartbeat - platform-layer').closest('a')?.getAttribute('href')).toBe(
      '/catalog/component/default/heartbeat',
    );
  });

  it("says who is built on this surface from the inverse catalogue relation", async () => {
    // The catalogue materialises `dependencyOf` on the target when another entry depends on
    // it, so this is the honest "what is built on this" answer, straight from the graph.
    neighbours['component:default/founder-console'] = {
      apiVersion: 'backstage.io/v1alpha1',
      kind: 'Component',
      metadata: {
        name: 'founder-console',
        namespace: 'default',
        title: 'Founder console',
      },
      spec: { type: 'founder-surface' },
    };
    const base: Entity = {
      apiVersion: 'backstage.io/v1alpha1',
      kind: 'Component',
      metadata: {
        name: 'inbox-api',
        namespace: 'default',
        title: 'Inbox API',
      },
      relations: [
        {
          type: 'dependencyOf',
          targetRef: 'component:default/founder-console',
        },
      ],
      spec: { type: 'platform-layer' },
    };
    await renderOne(base);
    await screen.findByText('Founder console - founder-surface');
    expect(screen.getByText('Used by')).toBeInTheDocument();
    expect(screen.getByText('Founder console - founder-surface').closest('a')?.getAttribute('href')).toBe(
      '/catalog/component/default/founder-console',
    );
  });

  it("states plainly when nothing in the catalogue is wired to it, never inventing a neighbour", async () => {
    await renderOne(unprobedSurface());
    await screen.findByText('Nothing else in the catalogue is wired to it yet.');
    expect(screen.getByText('What it talks to')).toBeInTheDocument();
    expect(
      screen.getByText('Nothing else in the catalogue is wired to it yet.'),
    ).toBeInTheDocument();
    // No fabricated relation names anywhere.
    expect(screen.queryByText(/Heartbeat/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Founder console/)).not.toBeInTheDocument();
  });
});
