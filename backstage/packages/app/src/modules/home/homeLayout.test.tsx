import { createElement } from 'react';
import { screen } from '@testing-library/react';
import {
  renderInTestApp,
  TestApiProvider,
  mockApis,
} from '@backstage/frontend-test-utils';
import { configApiRef } from '@backstage/frontend-plugin-api';
import type { HomePageLayoutProps } from '@backstage/plugin-home-react/alpha';
import { EstateHomeLayout, pickWidget, usedWidgets } from './homeLayout';

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
});
