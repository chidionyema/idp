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
import {
  accent,
  accentSoft,
  fontFamily,
  navy,
  navyRaised,
  paperWarm,
  phone,
  statusDark,
  statusLight,
} from './tokens';

export * from './tokens';

const pageThemes = {
  home: genPageTheme({ colors: [navy, '#2b3a55'], shape: shapes.wave }),
  documentation: genPageTheme({
    colors: ['#2b3a55', navy],
    shape: shapes.wave2,
  }),
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

// One type scale for the whole portal. The vendor default survived the rebrand
// until 2026-08-29 (crew#459 audit): headings were Helvetica at the stock sizes.
const typography = {
  fontFamily,
  htmlFontSize: 16,
  h1: {
    fontSize: 40,
    fontWeight: 700,
    letterSpacing: '-0.02em',
    lineHeight: 1.15,
  },
  h2: {
    fontSize: 30,
    fontWeight: 700,
    letterSpacing: '-0.015em',
    lineHeight: 1.2,
  },
  h3: { fontSize: 24, fontWeight: 600, lineHeight: 1.25 },
  h4: { fontSize: 20, fontWeight: 600, lineHeight: 1.3 },
  h5: { fontSize: 17, fontWeight: 600, lineHeight: 1.35 },
  h6: {
    fontSize: 15,
    fontWeight: 600,
    lineHeight: 1.4,
    letterSpacing: '0.01em',
  },
};

// Below 600px the stock layout breaks: the header's right-hand box (search,
// support) lands on top of the title, and the catalogue table squeezes six
// columns into a phone width so every cell wraps. Wrap the header; on a phone
// keep the first two columns of the catalogue table only (the name cell opens
// the entity page, which holds everything else). Founder screenshot, 2026-08-27
// (crew#459). The column rule is scoped to Backstage's Table: a global
// MuiTableCell rule also amputated dependency and task tables (audit 2026-08-29).
const components = {
  BackstageHeader: {
    styleOverrides: {
      header: {
        boxShadow: 'none',
        borderBottom: `3px solid ${accent}`,
        [phone]: { flexWrap: 'wrap', padding: '12px 16px', rowGap: 8 },
      },
      leftItemsBox: { [phone]: { flexBasis: '100%', minWidth: 0 } },
      rightItemsBox: {
        [phone]: { flexBasis: '100%', justifyContent: 'flex-start' },
      },
      title: { [phone]: { fontSize: '1.4rem', wordBreak: 'break-word' } },
    },
  },
  // Readable measure on a wide laptop, breathing room and the phone's safe area below.
  BackstageContent: {
    styleOverrides: {
      root: {
        maxWidth: 1280,
        width: '100%',
        marginLeft: 'auto',
        marginRight: 'auto',
        [phone]: {
          padding: 16,
          paddingBottom: 'calc(88px + env(safe-area-inset-bottom))',
        },
      },
    },
  },
  BackstageTable: {
    styleOverrides: {
      root: {
        [phone]: {
          '& td:nth-of-type(n+3), & th:nth-of-type(n+3)': { display: 'none' },
          '& td, & th': { padding: '8px 10px' },
        },
      },
    },
  },
  MuiCard: {
    styleOverrides: {
      root: {
        borderRadius: 12,
        boxShadow:
          '0 1px 2px rgba(20, 26, 38, 0.06), 0 8px 24px rgba(20, 26, 38, 0.06)',
      },
    },
  },
  MuiButton: {
    styleOverrides: {
      root: { textTransform: 'none', borderRadius: 8, fontWeight: 600 },
      contained: { boxShadow: 'none' },
    },
  },
  MuiChip: {
    styleOverrides: { root: { fontWeight: 600, borderRadius: 8 } },
  },
  MuiOutlinedInput: {
    styleOverrides: { root: { borderRadius: 10 } },
  },
};

export const estateLightTheme = createUnifiedTheme({
  ...createBaseThemeOptions({
    palette: {
      ...palettes.light,
      status: statusLight,
      primary: { main: '#b85a1c' },
      secondary: { main: '#2b3a55' },
      navigation: sidebar,
      background: { default: paperWarm, paper: '#ffffff' },
    },
    typography,
  }),
  defaultPageTheme: 'home',
  pageTheme: pageThemes,
  components,
});

export const estateDarkTheme = createUnifiedTheme({
  ...createBaseThemeOptions({
    palette: {
      ...palettes.dark,
      status: statusDark,
      primary: { main: accentSoft },
      secondary: { main: '#9fb3d9' },
      navigation: sidebar,
      background: { default: '#0f131b', paper: navyRaised },
    },
    typography,
  }),
  defaultPageTheme: 'home',
  pageTheme: pageThemes,
  components,
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
