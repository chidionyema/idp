import { createElement } from 'react';
import { screen } from '@testing-library/react';
import {
  renderInTestApp,
  TestApiProvider,
  mockApis,
} from '@backstage/frontend-test-utils';
import { configApiRef } from '@backstage/frontend-plugin-api';
import { catalogApiRef } from '@backstage/plugin-catalog-react';
import { catalogApiMock } from '@backstage/plugin-catalog-react/testUtils';
import { Entity } from '@backstage/catalog-model';
import type { HomePageLayoutProps } from '@backstage/plugin-home-react/alpha';
import { EstateHomeLayout, pickWidget, usedWidgets } from './homeLayout';
import { EVERYDAY_TITLE } from './everydayBand';

// Founder 2026-09-07: "why should i be looking for essential tools at all". The front page must
// carry his everyday tools, so the layout now reads the catalogue and the test gives it one.
const EVERYDAY_DOOR: Entity = {
  apiVersion: 'backstage.io/v1alpha1',
  kind: 'Component',
  metadata: {
    name: 'founder-screen',
    title: 'Estate Mac screen (in the browser)',
    annotations: { 'estate/group': 'Fix something', 'estate/tier': 'daily' },
    links: [{ url: 'https://example.test/screen/', title: 'Open' }],
  },
  spec: { type: 'founder-surface' },
};

const widget = (name: string, title = name) =>
  ({
    name,
    title,
    component: createElement('div', { id: name }),
  }) as unknown as HomePageLayoutProps['widgets'][number];

describe('pickWidget', () => {
  const widgets = [
    widget('home-page-search-bar', 'Search'),
    widget('home-page-toolkit', 'Toolkit'),
    widget('home-page-starred-entities', 'Starred'),
  ];

  it('finds a widget by a fragment of its name or title', () => {
    expect(pickWidget(widgets, 'search')?.props.id).toBe('home-page-search-bar');
    expect(pickWidget(widgets, 'toolkit')?.props.id).toBe('home-page-toolkit');
  });

  it('returns null when nothing matches', () => {
    expect(pickWidget(widgets, 'clock')).toBeNull();
  });

  it('leaves unmatched widgets for the leftover row', () => {
    const search = pickWidget(widgets, 'search');
    const rest = usedWidgets(widgets, [search]);
    expect(rest.map(w => w.name)).toEqual([
      'home-page-toolkit',
      'home-page-starred-entities',
    ]);
  });
});

describe('EstateHomeLayout', () => {
  it('puts Today, Find and Create on the page', async () => {
    await renderInTestApp(
      <TestApiProvider
        apis={[
          [
            configApiRef,
            mockApis.config({ data: { app: { title: 'Estate' } } }),
          ],
          [
            catalogApiRef,
            catalogApiMock({ entities: [EVERYDAY_DOOR] }),
          ],
        ]}
      >
        <EstateHomeLayout widgets={[]} />
      </TestApiProvider>,
    );
    expect(screen.getAllByText('Today').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Find').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Create').length).toBeGreaterThanOrEqual(1);
    expect(
      screen.getAllByText(/What needs you/).length,
    ).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Catalogue')).toBeInTheDocument();
    expect(screen.getByText('Every service we hold.')).toBeInTheDocument();
  });

  it('puts an everyday tool on the front page, so reaching it is never a search', async () => {
    await renderInTestApp(
      <TestApiProvider
        apis={[
          [
            configApiRef,
            mockApis.config({ data: { app: { title: 'Estate' } } }),
          ],
          [
            catalogApiRef,
            catalogApiMock({ entities: [EVERYDAY_DOOR] }),
          ],
        ]}
      >
        <EstateHomeLayout widgets={[]} />
      </TestApiProvider>,
    );
    expect(await screen.findByText(EVERYDAY_TITLE)).toBeInTheDocument();
    const tile = await screen.findByText(EVERYDAY_DOOR.metadata.title!);
    expect(tile).toBeInTheDocument();
    // The accessible name carries Backstage's "Opens in a new window" suffix on an external
    // link, so the name is matched from the start, the way Tools.test.tsx matches it.
    expect(
      await screen.findByRole('button', { name: /^Open Estate Mac screen/ }),
    ).toHaveAttribute('href', 'https://example.test/screen/');
  });
});
