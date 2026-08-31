// Nine doors and nothing else (crew#459 redesign, 2026-08-29). The vendor sidebar carried a
// search modal, a notifications bell, a visualizer and every plugin's page; the founder
// reads it on a phone. Backstage's own Sidebar stays underneath: it already collapses to a
// bottom bar below 600px (one tab per SidebarGroup) and handles focus and keyboard, so this
// is a list, not a component (LAW 43). Every page it hides is still published at its path
// and still graded by bin/idp-login-drill.
//
// crew#612 item 3: /#screens and /#kubernetes were hash-jumps that looked like pages;
// removed. Screens section is visible on Today (/). Kubernetes is in the catalog.
// crew#612 item 1: /create added; scaffolderPlugin registered in App.tsx.
// crew#612 item 3: DnsIcon for Kubernetes so Ops keeps the single gear icon.
import {
  Sidebar,
  SidebarDivider,
  SidebarGroup,
  SidebarItem,
  SidebarSpace,
} from '@backstage/core-components';
import { NavContentBlueprint } from '@backstage/plugin-app-react';
import TodayIcon from '@material-ui/icons/Today';
import LayersIcon from '@material-ui/icons/Layers';
import DnsIcon from '@material-ui/icons/Dns';
import AddCircleOutlineIcon from '@material-ui/icons/AddCircleOutline';
import AccountTreeIcon from '@material-ui/icons/AccountTree';
import TimelineIcon from '@material-ui/icons/Timeline';
import SearchIcon from '@material-ui/icons/Search';
import MenuBookIcon from '@material-ui/icons/MenuBook';
import AccountCircleIcon from '@material-ui/icons/AccountCircle';
import BuildIcon from '@material-ui/icons/Build';
import { SidebarLogo } from './SidebarLogo';

export const NAV = [
  { title: 'Today', to: '/', icon: TodayIcon },
  // crew#612: /#kubernetes was a hash-jump; catalog is the real route for cluster entities.
  { title: 'Kubernetes', to: '/catalog?filters%5Bkind%5D=Component', icon: DnsIcon },
  { title: 'What we run', to: '/catalog', icon: LayersIcon },
  // crew#612 item 1: templates on /create are the self-service menu.
  { title: 'Create', to: '/create', icon: AddCircleOutlineIcon },
  // Visual estate map: every system and its relations as a navigable graph (crew#612 10x).
  { title: 'Map', to: '/catalog-graph', icon: AccountTreeIcon },
  { title: 'Tools', to: '/tools', icon: BuildIcon },
  { title: 'Ops', to: '/ops', icon: TimelineIcon },
  { title: 'Find', to: '/search', icon: SearchIcon },
  { title: 'How-to', to: '/docs', icon: MenuBookIcon },
  { title: 'You', to: '/settings', icon: AccountCircleIcon },
] as const;

export const EstateNav = NavContentBlueprint.make({
  params: {
    component: ({ navItems }) => {
      // Every plugin's nav item is taken so nothing renders twice; the nine above are the nav.
      navItems.withComponent(() => null);
      return (
        <div data-testid="estate-nav">
          <Sidebar>
            <SidebarLogo />
            <SidebarDivider />
            {NAV.map(({ title, to, icon: Icon }) => (
              <SidebarGroup key={to} label={title} icon={<Icon />} to={to}>
                <SidebarItem icon={Icon} to={to} text={title} />
              </SidebarGroup>
            ))}
            <SidebarSpace />
          </Sidebar>
        </div>
      );
    },
  },
});
