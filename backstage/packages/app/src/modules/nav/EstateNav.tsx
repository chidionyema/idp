// Six doors and nothing else (crew#459 redesign, 2026-08-29). The vendor sidebar carried a
// search modal, a notifications bell, a visualizer and every plugin's page; the founder
// reads it on a phone. Backstage's own Sidebar stays underneath: it already collapses to a
// bottom bar below 600px (one tab per SidebarGroup) and handles focus and keyboard, so this
// is a list, not a component (LAW 43). Every page it hides is still published at its path
// and still graded by bin/idp-login-drill.
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
import DesktopWindowsIcon from '@material-ui/icons/DesktopWindows';
import SettingsApplicationsIcon from '@material-ui/icons/SettingsApplications';
import SearchIcon from '@material-ui/icons/Search';
import MenuBookIcon from '@material-ui/icons/MenuBook';
import AccountCircleIcon from '@material-ui/icons/AccountCircle';
import BuildIcon from '@material-ui/icons/Build';
import { SidebarLogo } from './SidebarLogo';

export const NAV = [
  { title: 'Today', to: '/', icon: TodayIcon },
  // crew#612 CP11: the screens (Langfuse, SigNoz, the scheduler ...) one tap from anywhere.
  { title: 'Screens', to: '/#screens', icon: DesktopWindowsIcon },
  // founder, 2026-08-29, for the umpteenth time: "where are all the k8s tooling".
  { title: 'Kubernetes', to: '/#kubernetes', icon: SettingsApplicationsIcon },
  { title: 'What we run', to: '/catalog', icon: LayersIcon },
  { title: 'Tools', to: '/tools', icon: BuildIcon },
  { title: 'Ops', to: '/ops', icon: SettingsApplicationsIcon },
  { title: 'Find', to: '/search', icon: SearchIcon },
  { title: 'How-to', to: '/docs', icon: MenuBookIcon },
  { title: 'You', to: '/settings', icon: AccountCircleIcon },
] as const;

export const EstateNav = NavContentBlueprint.make({
  params: {
    component: ({ navItems }) => {
      // Every plugin's nav item is taken so nothing renders twice; the six above are the nav.
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
