// These tests grade what a person reads on the estate entity overview tab (founder,
// "clicking needs more detail and overview"): the estate facts bin/catalog-gen wrote on the
// entity, its category membership, and that a linked relation takes a person deeper into the
// catalogue instead of leaving it. No layout words, no selectors (R53); visible text finds it.
import { renderInTestApp } from '@backstage/frontend-test-utils';
import { EntityProvider } from '@backstage/plugin-catalog-react';
import { Entity } from '@backstage/catalog-model';
import { screen } from '@testing-library/react';
import { EstateOverview } from './index';

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

const renderOne = (entity: Entity) =>
  renderInTestApp(
    <EntityProvider entity={entity}>
      <EstateOverview />
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
});
