// These tests grade what a person reads on the estate entity overview tab (founder,
// "clicking needs more detail and overview"): the estate facts bin/catalog-gen wrote on the
// entity, its category membership, and that a linked relation takes a person deeper into the
// catalogue instead of leaving it. No layout words, no selectors (R53); visible text finds it.
import { renderInTestApp } from '@backstage/frontend-test-utils';
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

const renderOne = (entity: Entity, now: number = Date.now()) =>
  renderInTestApp(
    <EntityProvider entity={entity}>
      <EstateOverview now={now} />
    </EntityProvider>,
  );

describe('EstateOverview (the owned estate entity detail tab)', () => {
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

  it('claims no estate fact for a hand-authored entity', async () => {
    await renderOne(handAuthored());
    expect(screen.getByText('The dashboard')).toBeInTheDocument();
    // No estate/ fact block is rendered for a non-generated entry.
    expect(screen.queryByText('Rows')).not.toBeInTheDocument();
    expect(screen.queryByText('Coupling')).not.toBeInTheDocument();
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
});
