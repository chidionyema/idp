// The front page layout. Backstage still supplies every widget; this file only
// arranges them. The plugin's drag-and-resize board was the 2020 interaction, and it
// is the interaction the founder called outdated (2026-09-03). A layout is
// allowed by HomePageLayoutBlueprint; the plugin docs say so.
import { useMemo } from 'react';
import type { ReactElement } from 'react';
import { configApiRef, useApi } from '@backstage/frontend-plugin-api';
import type { HomePageLayoutProps } from '@backstage/plugin-home-react/alpha';
import { Content, Header, LinkButton, Page } from '@backstage/core-components';
import { makeStyles } from '@material-ui/core';
import { phone } from '../theme/tokens';

const useStyles = makeStyles(theme => ({
  shell: {
    display: 'grid',
    gridTemplateColumns: 'minmax(0, 1.45fr) minmax(260px, 0.8fr)',
    gap: theme.spacing(3),
    alignItems: 'start',
    [phone]: { gridTemplateColumns: '1fr' },
  },
  search: { gridColumn: '1 / -1' },
  tools: { minWidth: 0 },
  aside: {
    display: 'flex',
    flexDirection: 'column',
    gap: theme.spacing(2),
    minWidth: 0,
  },
  rest: {
    gridColumn: '1 / -1',
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
    gap: theme.spacing(2),
  },
  actions: { display: 'flex', gap: theme.spacing(1), flexWrap: 'wrap' },
}));

export function pickWidget(
  widgets: HomePageLayoutProps['widgets'],
  ...needles: string[]
): ReactElement | null {
  const hit = widgets.find(widget => {
    const hay = `${widget.name ?? ''} ${widget.title ?? ''}`.toLowerCase();
    return needles.some(needle => hay.includes(needle.toLowerCase()));
  });
  return hit?.component ?? null;
}

export function usedWidgets(
  widgets: HomePageLayoutProps['widgets'],
  placed: Array<ReactElement | null>,
): HomePageLayoutProps['widgets'] {
  const placedSet = new Set(placed.filter(Boolean));
  return widgets.filter(widget => !placedSet.has(widget.component));
}

export function EstateHomeLayout({ widgets }: HomePageLayoutProps) {
  const classes = useStyles();
  const brand = useApi(configApiRef).getOptionalString('app.title') ?? 'Estate';
  const search = pickWidget(widgets, 'search');
  const tools = pickWidget(widgets, 'toolkit', 'tools');
  const starred = pickWidget(widgets, 'starred');
  const recently = pickWidget(widgets, 'recently');
  const most = pickWidget(widgets, 'most visited', 'top visited');
  const leftover = useMemo(
    () => usedWidgets(widgets, [search, tools, starred, recently, most]),
    [widgets, search, tools, starred, recently, most],
  );

  return (
    <Page themeId="home">
      <Header
        title="Today"
        subtitle={`${brand}. What needs you, and every door into the estate.`}
      >
        <div className={classes.actions}>
          <LinkButton to="/search" variant="outlined">
            Find
          </LinkButton>
          <LinkButton to="/create" color="primary" variant="contained">
            Create
          </LinkButton>
        </div>
      </Header>
      <Content>
        <div className={classes.shell}>
          {search && <div className={classes.search}>{search}</div>}
          {tools && <div className={classes.tools}>{tools}</div>}
          <aside className={classes.aside}>
            {starred}
            {recently}
            {most}
          </aside>
          {leftover.length > 0 && (
            <div className={classes.rest}>
              {leftover.map((widget, index) => (
                <div key={widget.name ?? index}>{widget.component}</div>
              ))}
            </div>
          )}
        </div>
      </Content>
    </Page>
  );
}
