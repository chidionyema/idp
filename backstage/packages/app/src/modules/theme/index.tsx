// The estate's own look (crew#459 redesign, 2026-08-29). Backstage ships two default themes
// named `light` and `dark` under the `app` plugin; a module for that plugin with the same
// names replaces them, so the theme picker in Settings still shows two entries and the
// user's stored choice still applies.
//
// Every page header is flat: `shape: 'none'` is a legal background-image layer, so the
// vendor's wave is gone from every page without touching any plugin. Elevation is a border,
// not a shadow; the only two shadows in the system are the palette and the sticky header.
import { createFrontendModule } from '@backstage/frontend-plugin-api';
import { ThemeBlueprint } from '@backstage/plugin-app-react';
import {
  UnifiedThemeProvider,
  createBaseThemeOptions,
  createUnifiedTheme,
  genPageTheme,
  palettes,
  BackstageTypography,
} from '@backstage/theme';
import LightIcon from '@material-ui/icons/WbSunny';
import DarkIcon from '@material-ui/icons/Brightness2';
import {
  Tone,
  dark,
  ease,
  fontFamily,
  light,
  phone,
  reducedMotion,
  statusDark,
  statusLight,
} from './tokens';

export * from './tokens';

// The type scale (founder 2026-08-29: "why is headers same size colour as subheading? how do
// you know which is which"). Each step differs from the next in at least two of size, weight
// and colour; a subheading is body-sized and secondary-coloured, never a smaller heading.
const typography: BackstageTypography = {
  fontFamily,
  htmlFontSize: 16,
  h1: { fontSize: 40, marginBottom: 12, fontWeight: 700 },
  h2: { fontSize: 24, marginBottom: 8, fontWeight: 700 },
  h3: { fontSize: 17, marginBottom: 6, fontWeight: 600 },
  h4: { fontSize: 15, marginBottom: 4, fontWeight: 600 },
  h5: { fontSize: 14, marginBottom: 4, fontWeight: 600 },
  h6: { fontSize: 13, marginBottom: 4, fontWeight: 600 },
};

const pageThemesFor = (t: Tone) => {
  const flat = genPageTheme({
    colors: [t.canvas],
    shape: 'none',
    options: { fontColor: t.textPrimary },
  });
  return {
    home: flat,
    documentation: flat,
    tool: flat,
    service: flat,
    website: flat,
    library: flat,
    other: flat,
    app: flat,
    apis: flat,
  };
};

const componentsFor = (t: Tone) => ({
  MuiCssBaseline: {
    styleOverrides: {
      html: {
        WebkitFontSmoothing: 'antialiased',
        MozOsxFontSmoothing: 'grayscale',
      },
      body: { overscrollBehaviorY: 'none', backgroundColor: t.canvas },
      '*::-webkit-scrollbar': { width: 10, height: 10 },
      '*::-webkit-scrollbar-thumb': {
        background: t.borderStrong,
        borderRadius: 8,
      },
      'a:focus-visible, button:focus-visible, [role="button"]:focus-visible, input:focus-visible':
        {
          outline: 'none',
          boxShadow: `0 0 0 2px ${t.canvas}, 0 0 0 4px ${t.accent}`,
        },
      [reducedMotion]: {
        '*, *::before, *::after': {
          animationDuration: '0.01ms !important',
          transitionDuration: '0.01ms !important',
          scrollBehavior: 'auto !important',
        },
      },
    },
  },
  BackstageHeader: {
    styleOverrides: {
      header: {
        backgroundImage: 'none',
        backgroundColor: t.canvas,
        boxShadow: 'none',
        padding: '16px 24px 12px',
        minHeight: 0,
        borderBottom: `1px solid ${t.borderSubtle}`,
        [phone]: { flexWrap: 'wrap', padding: '12px 16px', rowGap: 8 },
      },
      title: {
        fontSize: '1.5rem',
        fontWeight: 600,
        lineHeight: 1.2,
        letterSpacing: '-0.015em',
        color: t.textPrimary,
        [phone]: { fontSize: '1.25rem', wordBreak: 'break-word' },
      },
      subtitle: { fontSize: '0.875rem', color: t.textSecondary, marginTop: 2 },
      type: {
        fontSize: '0.75rem',
        color: t.textMuted,
        textTransform: 'none',
        letterSpacing: 0,
      },
      breadcrumb: { color: t.textMuted },
      leftItemsBox: { [phone]: { flexBasis: '100%', minWidth: 0 } },
      rightItemsBox: {
        [phone]: { flexBasis: '100%', justifyContent: 'flex-start' },
      },
    },
  },
  BackstageHeaderLabel: {
    styleOverrides: {
      label: { color: t.textMuted, textTransform: 'none' },
      value: { color: t.textPrimary },
    },
  },
  BackstageContent: {
    styleOverrides: {
      root: {
        maxWidth: 1280,
        width: '100%',
        marginLeft: 'auto',
        marginRight: 'auto',
        backgroundColor: t.canvas,
        [phone]: {
          padding: 16,
          paddingBottom: 'calc(88px + env(safe-area-inset-bottom))',
        },
      },
    },
  },
  BackstageInfoCard: {
    styleOverrides: {
      header: { padding: '16px 20px 8px' },
      headerTitle: { fontSize: 16, fontWeight: 600 },
      headerSubheader: { fontSize: 13, fontWeight: 400, color: t.textSecondary },
    },
  },
  // On a phone the catalogue table keeps its first two columns; the name cell opens the
  // entity page, which holds everything else (founder screenshot 2026-08-27).
  BackstageTable: {
    styleOverrides: {
      root: {
        '& th': {
          textTransform: 'none',
          fontWeight: 600,
          color: t.textMuted,
          letterSpacing: 0,
        },
        [phone]: {
          '& td:nth-of-type(n+3), & th:nth-of-type(n+3)': { display: 'none' },
          '& td, & th': { padding: '8px 10px' },
        },
      },
    },
  },
  MuiPaper: {
    styleOverrides: {
      root: { backgroundImage: 'none' },
      elevation1: { boxShadow: 'none', border: `1px solid ${t.border}` },
      elevation2: { boxShadow: 'none', border: `1px solid ${t.border}` },
    },
  },
  MuiCard: {
    styleOverrides: {
      root: {
        borderRadius: 14,
        boxShadow: 'none',
        border: `1px solid ${t.border}`,
        backgroundColor: t.surface1,
        transition: `border-color 160ms ${ease}, transform 160ms ${ease}, box-shadow 160ms ${ease}`,
        '&:hover': {
          borderColor: t.borderStrong,
          transform: 'translateY(-1px)',
          boxShadow: `0 8px 24px ${t.canvas === '#ffffff' ? 'rgba(15,23,42,.06)' : 'rgba(0,0,0,.35)'}`,
        },
      },
    },
  },
  MuiButton: {
    styleOverrides: {
      root: {
        textTransform: 'none',
        borderRadius: 10,
        fontWeight: 600,
        letterSpacing: 0,
        minHeight: 40,
        padding: '8px 16px',
        transition: `background-color 120ms ${ease}, color 120ms ${ease}, border-color 120ms ${ease}`,
      },
      contained: { boxShadow: 'none', '&:hover': { boxShadow: 'none' } },
      outlined: { borderColor: t.border },
    },
  },
  MuiChip: {
    styleOverrides: {
      root: {
        fontWeight: 600,
        borderRadius: 999,
        height: 24,
        fontSize: 12,
        textTransform: 'none',
      },
    },
  },
  MuiOutlinedInput: {
    styleOverrides: {
      root: { borderRadius: 10, backgroundColor: t.surface1, minHeight: 40 },
      notchedOutline: { borderColor: t.border },
    },
  },
  MuiTooltip: {
    styleOverrides: {
      tooltip: {
        backgroundColor: t.surface2,
        color: t.textPrimary,
        border: `1px solid ${t.border}`,
        fontSize: 12,
      },
    },
  },
  MuiTabs: {
    styleOverrides: {
      indicator: { backgroundColor: t.accent, height: 2 },
    },
  },
  MuiTab: {
    styleOverrides: {
      root: { textTransform: 'none', fontWeight: 600, letterSpacing: 0 },
    },
  },
  MuiDialog: {
    styleOverrides: {
      paper: {
        borderRadius: 16,
        border: `1px solid ${t.border}`,
        boxShadow: '0 16px 40px rgba(0,0,0,.55)',
      },
    },
  },
});

const navigationFor = (t: Tone) => ({
  background: t.canvas,
  indicator: t.accent,
  selectedColor: t.textPrimary,
  color: t.textMuted,
  navItem: { hoverBackground: t.surface3 },
  submenu: { background: t.surface2 },
  pinnedBackground: t.canvas,
});

export const estateLightTheme = createUnifiedTheme({
  ...createBaseThemeOptions({
    palette: {
      ...palettes.light,
      status: statusLight,
      primary: { main: light.accent, contrastText: light.inkOnAccent },
      secondary: { main: light.textSecondary },
      navigation: navigationFor(light),
      background: { default: light.canvas, paper: light.surface2 },
      text: { primary: light.textPrimary, secondary: light.textSecondary },
      divider: light.borderSubtle,
    },
    typography,
  }),
  defaultPageTheme: 'home',
  pageTheme: pageThemesFor(light),
  components: componentsFor(light),
});

export const estateDarkTheme = createUnifiedTheme({
  ...createBaseThemeOptions({
    palette: {
      ...palettes.dark,
      status: statusDark,
      primary: { main: dark.accent, contrastText: dark.inkOnAccent },
      secondary: { main: dark.textSecondary },
      navigation: navigationFor(dark),
      background: { default: dark.canvas, paper: dark.surface1 },
      text: { primary: dark.textPrimary, secondary: dark.textSecondary },
      divider: dark.borderSubtle,
    },
    typography,
  }),
  defaultPageTheme: 'home',
  pageTheme: pageThemesFor(dark),
  components: componentsFor(dark),
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
