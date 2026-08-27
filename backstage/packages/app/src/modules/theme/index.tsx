// The estate's own look. Backstage ships two default themes named `light` and
// `dark` under the `app` plugin; a module for that plugin with the same names
// replaces them, so the theme picker in Settings still shows two entries and the
// user's stored choice still applies. crew#459: an investor must see the estate,
// not the vendor's teal.
import { createFrontendModule } from '@backstage/frontend-plugin-api';
import { ThemeBlueprint } from '@backstage/plugin-app-react';
import {
  UnifiedThemeProvider,
  createBaseThemeOptions,
  createUnifiedTheme,
  genPageTheme,
  palettes,
  shapes,
} from '@backstage/theme';
import LightIcon from '@material-ui/icons/WbSunny';
import DarkIcon from '@material-ui/icons/Brightness2';

const accent = '#e0762a';
const accentSoft = '#f2b64b';
const navy = '#141a26';
const navyRaised = '#1c2433';

const pageThemes = {
  home: genPageTheme({ colors: [navy, '#2b3a55'], shape: shapes.wave }),
  documentation: genPageTheme({ colors: ['#2b3a55', navy], shape: shapes.wave2 }),
  tool: genPageTheme({ colors: [navyRaised, navy], shape: shapes.round }),
  service: genPageTheme({ colors: [navy, '#3d2a1d'], shape: shapes.wave }),
  website: genPageTheme({ colors: [navy, '#2b3a55'], shape: shapes.wave }),
  library: genPageTheme({ colors: [navy, navyRaised], shape: shapes.wave }),
  other: genPageTheme({ colors: [navy, navyRaised], shape: shapes.wave }),
  app: genPageTheme({ colors: [navy, '#2b3a55'], shape: shapes.wave }),
  apis: genPageTheme({ colors: [navy, '#2b3a55'], shape: shapes.wave2 }),
};

const sidebar = {
  background: navy,
  indicator: accent,
  selectedColor: accentSoft,
  color: '#c9cfda',
  navItem: { hoverBackground: navyRaised },
  submenu: { background: navyRaised },
  pinnedBackground: navy,
};

export const estateLightTheme = createUnifiedTheme({
  ...createBaseThemeOptions({
    palette: {
      ...palettes.light,
      primary: { main: '#b85a1c' },
      secondary: { main: '#2b3a55' },
      navigation: sidebar,
      background: { default: '#f6f4ef', paper: '#ffffff' },
    },
  }),
  defaultPageTheme: 'home',
  pageTheme: pageThemes,
  components: {
    BackstageHeader: {
      styleOverrides: {
        header: { boxShadow: 'none', borderBottom: `3px solid ${accent}` },
      },
    },
  },
});

export const estateDarkTheme = createUnifiedTheme({
  ...createBaseThemeOptions({
    palette: {
      ...palettes.dark,
      primary: { main: accentSoft },
      secondary: { main: '#9fb3d9' },
      navigation: sidebar,
      background: { default: '#0f131b', paper: navyRaised },
    },
  }),
  defaultPageTheme: 'home',
  pageTheme: pageThemes,
  components: {
    BackstageHeader: {
      styleOverrides: {
        header: { boxShadow: 'none', borderBottom: `3px solid ${accent}` },
      },
    },
  },
});

const lightTheme = ThemeBlueprint.make({
  name: 'light',
  params: {
    theme: {
      id: 'light',
      title: 'Estate light',
      variant: 'light',
      icon: <LightIcon />,
      Provider: ({ children }) => (
        <UnifiedThemeProvider theme={estateLightTheme} children={children} />
      ),
    },
  },
});

const darkTheme = ThemeBlueprint.make({
  name: 'dark',
  params: {
    theme: {
      id: 'dark',
      title: 'Estate dark',
      variant: 'dark',
      icon: <DarkIcon />,
      Provider: ({ children }) => (
        <UnifiedThemeProvider theme={estateDarkTheme} children={children} />
      ),
    },
  },
});

export const themeModule = createFrontendModule({
  pluginId: 'app',
  extensions: [lightTheme, darkTheme],
});
