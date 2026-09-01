// The front page at "/" is Backstage's own home page: `page:home` from @backstage/plugin-home,
// laid out from app-config.yaml (founder, 2026-09-01: "use Backstage templates", "so don't
// bother"). Until then a module page with the default name overrode `page:home` with the god
// view (crew#459), 1,200 lines of this repository's own design in one long scroll. That page
// is kept at /estate, unlinked, until its numbers become widgets; nothing at "/" is ours.
//
// The layout is the one Backstage documents for a custom home page layout
// (https://backstage.io/docs/getting-started/homepage/): Page, Header, Content and the
// plugin's CustomHomepageGrid, with the grid seeded from `page:home`'s `defaultConfig` exactly
// as the plugin's own DefaultHomePageLayout seeds it. The only addition is the Header, so the
// page carries the estate's name (app.title) like every other Backstage page.
import { Fragment, useMemo } from 'react';
import {
  configApiRef,
  createFrontendModule,
  PageBlueprint,
  useApi,
} from '@backstage/frontend-plugin-api';
import {
  HomePageLayoutBlueprint,
  type HomePageLayoutProps,
} from '@backstage/plugin-home-react/alpha';
import { CustomHomepageGrid } from '@backstage/plugin-home';
import { Content, Header, Page } from '@backstage/core-components';

export function EstateHomeLayout({ widgets, defaultConfig }: HomePageLayoutProps) {
  const brand = useApi(configApiRef).getOptionalString('app.title') ?? 'Estate';
  const gridConfig = useMemo(
    () =>
      defaultConfig?.map(item => ({
        component: item.component,
        x: item.column,
        y: item.row,
        width: item.width,
        height: item.height,
        movable: item.movable,
        deletable: item.deletable,
        resizable: item.resizable,
      })),
    [defaultConfig],
  );
  return (
    <Page themeId="home">
      <Header title={brand} />
      <Content>
        <CustomHomepageGrid config={gridConfig}>
          {widgets.map((widget, index) => (
            <Fragment key={widget.name ?? index}>{widget.component}</Fragment>
          ))}
        </CustomHomepageGrid>
      </Content>
    </Page>
  );
}

const homeLayout = HomePageLayoutBlueprint.make({
  params: {
    loader: async () => EstateHomeLayout,
  },
});

// /estate: the crew#459 god view, one card per founder-surface entity, kept off the front
// page and off the menu. Graded by bin/idp-login-drill like every other published path.
const estatePage = PageBlueprint.make({
  name: 'estate',
  params: {
    path: '/estate',
    loader: () => import('./EstateHome').then(m => <m.EstateHome />),
  },
});

// /pair: the founder types Moonlight's PIN into the portal and it reaches Sunshine on the
// Mac over the proxy (crew#562, founder-screen-access path 1). Listed as a founder surface
// in backstage/founder/catalog-info.yaml so the crew#401 gate and the god view carry it.
const pairPhonePage = PageBlueprint.make({
  name: 'pair',
  params: {
    path: '/pair',
    loader: () => import('./PairPhone').then(m => <m.PairPhone />),
  },
});

// /tools: every door on one page, grouped from the catalogue (crew#684 CP0, founder
// 2026-08-30: "another page in backstage just pure tools"). Listed as a founder surface in
// backstage/founder/catalog-info.yaml so the crew#401 gate and the login drill carry it.
const toolsPage = PageBlueprint.make({
  name: 'tools',
  params: {
    path: '/tools',
    loader: () => import('./Tools').then(m => <m.Tools />),
  },
});

// crew#684 CP1: the Ops dashboard, "I need to see everything". The cluster tile first; the
// open-reds table, founder tiles and the drills row land on the same page in later checkpoints.
const opsPage = PageBlueprint.make({
  name: 'ops',
  params: {
    path: '/ops',
    loader: () => import('./Ops').then(m => <m.Ops />),
  },
});

export const homeModule = createFrontendModule({
  pluginId: 'home',
  extensions: [homeLayout, estatePage, pairPhonePage, toolsPage, opsPage],
});
