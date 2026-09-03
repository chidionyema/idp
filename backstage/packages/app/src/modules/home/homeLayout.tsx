// The front page layout. Backstage supplies search; the ten doors are drawn here as
// Backstage UI cards. The visit and starred cards are empty for a visitor and are not
// placed (app-config.yaml); the layout still seats them if a config ever adds them. The
// plugin's stamp-sized toolkit is the 2020 look and is not placed (the widget stays
// installed).
//
// Header, search, doors and visits share one column inside Content. A BUI Header
// outside Content used its own container and sat at a different width to the
// page, which broke the landing layout (founder 2026-09-03).
import { useMemo } from 'react';
import type { ReactElement } from 'react';
import { configApiRef, useApi } from '@backstage/frontend-plugin-api';
import type { HomePageLayoutProps } from '@backstage/plugin-home-react/alpha';
import { Content, Page } from '@backstage/core-components';
import { ButtonLink, Flex, Grid, Header } from '@backstage/ui';
import { RiAddCircleLine, RiSearchLine } from '@remixicon/react';
import { DoorGrid } from './DoorGrid';

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
  const brand = useApi(configApiRef).getOptionalString('app.title') ?? 'Estate';
  const search = pickWidget(widgets, 'search');
  const toolkit = pickWidget(widgets, 'toolkit', 'tools');
  const starred = pickWidget(widgets, 'starred');
  const recently = pickWidget(widgets, 'recently');
  const most = pickWidget(widgets, 'most visited', 'top visited');
  const leftover = useMemo(
    () => usedWidgets(widgets, [search, toolkit, starred, recently, most]),
    [widgets, search, toolkit, starred, recently, most],
  );
  const visits = [starred, recently, most, ...leftover.map(w => w.component)].filter(
    Boolean,
  );

  return (
    <Page themeId="home">
      <Content>
        <div className="estate-today">
          <Flex direction="column" gap="5">
            <Header
              title="Today"
              description={`${brand}. What needs you, and every door into the estate.`}
              customActions={
                <Flex gap="2">
                  <ButtonLink
                    href="/search"
                    variant="secondary"
                    size="medium"
                    iconStart={<RiSearchLine />}
                  >
                    Find
                  </ButtonLink>
                  <ButtonLink
                    href="/create"
                    variant="primary"
                    size="medium"
                    iconStart={<RiAddCircleLine />}
                  >
                    Create
                  </ButtonLink>
                </Flex>
              }
            />
            {search && <div className="estate-today-search">{search}</div>}
            <DoorGrid />
            {visits.length > 0 && (
              <Grid.Root
                className="estate-today-aside"
                columns={{
                  initial: '1',
                  md:
                    visits.length >= 3 ? '3' : visits.length === 2 ? '2' : '1',
                }}
                gap="4"
              >
                {visits.map((node, index) => (
                  <Grid.Item key={index}>{node}</Grid.Item>
                ))}
              </Grid.Root>
            )}
          </Flex>
        </div>
      </Content>
    </Page>
  );
}
