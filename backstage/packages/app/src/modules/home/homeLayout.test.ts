import { createElement } from 'react';
import type { HomePageLayoutProps } from '@backstage/plugin-home-react/alpha';
import { pickWidget, usedWidgets } from './homeLayout';

const widget = (name: string, title = name) =>
  ({
    name,
    title,
    component: createElement('div', { id: name }),
  }) as HomePageLayoutProps['widgets'][number];

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
