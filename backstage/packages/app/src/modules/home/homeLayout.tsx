// The front page layout. Backstage supplies search; the ten doors are drawn here as
// Backstage UI cards. The visit and starred cards are empty for a visitor and are not
// placed (app-config.yaml); the layout still seats them if a config ever adds them. The plugin's stamp-sized
// toolkit is the 2020 look and is not placed (the widget stays installed).
import { useMemo } from 'react';
import type { ReactElement } from 'react';
import { configApiRef, useApi } from '@backstage/frontend-plugin-api';
import type { HomePageLayoutProps } from '@backstage/plugin-home-react/alpha';
import { Content, Page } from '@backstage/core-components';
import { ButtonLink, Flex, Grid, Header, Text } from '@backstage/ui';
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

  return (
    <Page themeId="home">
      <Header
        title="Today"
        tags={[{ label: brand }]}
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
      <Content>
        <Flex direction="column" gap="6">
          {search && <div className="estate-today-search">{search}</div>}
          <Flex direction="column" gap="3">
            <Text as="h2" variant="title-medium" weight="bold">
              Doors
            </Text>
            <DoorGrid />
          </Flex>
          {(starred || recently || most || leftover.length > 0) && (
            <Grid.Root columns={{ initial: '1', md: '12' }} gap="4">
              {(starred || recently || most) && (
                <Grid.Item colSpan={{ initial: '1', md: '4' }}>
                  <div className="estate-today-aside">
                    <Flex direction="column" gap="4">
                      {starred}
                      {recently}
                      {most}
                    </Flex>
                  </div>
                </Grid.Item>
              )}
              {leftover.map((widget, index) => (
                <Grid.Item
                  key={widget.name ?? index}
                  colSpan={{ initial: '1', md: '4' }}
                >
                  <div className="estate-today-aside">{widget.component}</div>
                </Grid.Item>
              ))}
            </Grid.Root>
          )}
        </Flex>
      </Content>
    </Page>
  );
}
