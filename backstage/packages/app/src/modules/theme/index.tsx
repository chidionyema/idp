// The estate's own look (crew#459 redesign, 2026-08-29). Backstage ships two default themes
// named `light` and `dark` under the `app` plugin; a module for that plugin with the same
// names replaces them, so the theme picker in Settings still shows two entries and the
// user's stored choice still applies.
//
// Every page header is flat: `shape: 'none'` is a legal background-image layer, so the
// vendor's wave is gone from every page without touching any plugin. Elevation is a border,
// not a shadow; the only two shadows in the system are the palette and the sticky header.
//
// Inner-page polish pass (founder 2026-09-04: "spectacular, better language, more intuitive"):
// BackstageHeader title raised to clamp(1.5rem,2.5vw,2rem)/700 so Catalog, APIs, Docs,
// Create, Search, Settings, entity pages open with the same visual weight as BUI Header
// on Today/Tools/Ops. New overrides: MuiTableRow hover, MuiAlert, MuiStepper, MuiStepIcon,
// MuiLinearProgress, MuiTableCell, MuiListItem, MuiMenu, MuiPopover, MuiCardHeader,
// MuiCardContent — every component a plugin page touches, at-theme level once.
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
  stateDark,
  stateLight,
  statusDark,
  statusLight,
} from './tokens';
import { buiVars } from './buiVars';

export * from './tokens';

// The type scale (founder 2026-08-29). Each step differs in at least two of size, weight,
// colour; a subheading is body-sized and secondary-coloured, never a smaller heading.
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

const componentsFor = (t: Tone, states: typeof stateDark) => ({
  MuiCssBaseline: {
    styleOverrides: {
      html: {
        WebkitFontSmoothing: 'antialiased',
        MozOsxFontSmoothing: 'grayscale',
      },
      '[data-theme-mode]': buiVars(t, states),
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
  // ── BackstageHeader ────────────────────────────────────────────────────────
  // Title raised from 1.5rem/600 → clamp(1.5rem,2.5vw,2rem)/700.
  // Affects every plugin page that uses BackstageHeader: Catalog, APIs, Docs,
  // Create, Search, Settings, entity pages. Padding lifted to match BUI Header.
  BackstageHeader: {
    styleOverrides: {
      header: {
        backgroundImage: 'none',
        backgroundColor: t.canvas,
        boxShadow: 'none',
        padding: '20px 24px 16px',
        minHeight: 0,
        borderBottom: `1px solid ${t.borderSubtle}`,
        [phone]: { flexWrap: 'wrap', padding: '14px 16px 12px', rowGap: 8 },
      },
      title: {
        fontSize: 'clamp(1.5rem, 2.5vw, 2rem)',
        fontWeight: 700,
        lineHeight: 1.15,
        letterSpacing: '-0.02em',
        color: t.textPrimary,
        [phone]: { fontSize: '1.25rem', wordBreak: 'break-word' },
      },
      subtitle: {
        fontSize: '0.9375rem',
        lineHeight: 1.5,
        color: t.textSecondary,
        marginTop: 4,
        maxWidth: 600,
      },
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
  // ── BackstageContent ───────────────────────────────────────────────────────
  // 24px desktop padding matches the home-page grid rhythm.
  BackstageContent: {
    styleOverrides: {
      root: {
        maxWidth: 1280,
        width: '100%',
        marginLeft: 'auto',
        marginRight: 'auto',
        backgroundColor: t.canvas,
        padding: '24px',
        [phone]: {
          padding: 16,
          paddingBottom: 'calc(88px + env(safe-area-inset-bottom))',
        },
      },
    },
  },
  BackstageInfoCard: {
    styleOverrides: {
      header: { padding: '20px 24px 12px' },
      headerTitle: { fontSize: 17, fontWeight: 600, letterSpacing: '-0.01em' },
      headerSubheader: { fontSize: 13, fontWeight: 400, color: t.textSecondary },
    },
  },
  // ── BackstageTable ─────────────────────────────────────────────────────────
  // Added td font-size and tbody row hover (same surface-1 lift as home tiles).
  BackstageTable: {
    styleOverrides: {
      root: {
        '& th': {
          textTransform: 'none',
          fontWeight: 600,
          color: t.textMuted,
          letterSpacing: 0,
          fontSize: '0.8125rem',
        },
        '& td': {
          fontSize: '0.875rem',
          color: t.textPrimary,
        },
        '& tbody tr:hover': {
          backgroundColor: t.surface1,
        },
        [phone]: {
          '& td:nth-of-type(n+3), & th:nth-of-type(n+3)': { display: 'none' },
          '& td, & th': { padding: '8px 10px' },
        },
      },
    },
  },
  // ── MuiPaper / MuiCard ────────────────────────────────────────────────────
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
        borderRadius: 16,
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
  MuiCardHeader: {
    styleOverrides: {
      root: { padding: '20px 20px 12px' },
      title: { fontSize: 17, fontWeight: 600, letterSpacing: '-0.01em' },
      subheader: { fontSize: 13, color: t.textSecondary, marginTop: 2 },
    },
  },
  MuiCardContent: {
    styleOverrides: {
      root: { padding: '0 20px 20px', '&:last-child': { paddingBottom: 20 } },
    },
  },
  // ── Buttons ────────────────────────────────────────────────────────────────
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
  // ── Inputs ─────────────────────────────────────────────────────────────────
  MuiOutlinedInput: {
    styleOverrides: {
      root: { borderRadius: 12, backgroundColor: t.surface1, minHeight: 44 },
      notchedOutline: { borderColor: t.border },
    },
  },
  MuiFormLabel: {
    styleOverrides: {
      root: {
        fontSize: '0.875rem',
        fontWeight: 500,
        color: t.textSecondary,
        '&$focused': { color: t.accent },
      },
    },
  },
  MuiInputLabel: {
    styleOverrides: {
      root: { fontSize: '0.875rem', color: t.textSecondary },
    },
  },
  MuiSelect: {
    styleOverrides: {
      root: { borderRadius: 12 },
      icon: { color: t.textMuted },
    },
  },
  MuiCheckbox: {
    styleOverrides: {
      root: { color: t.border, '&$checked': { color: t.accent } },
    },
  },
  MuiSwitch: {
    styleOverrides: {
      track: { backgroundColor: t.border },
      switchBase: {
        '&$checked': { color: t.accent },
        '&$checked + $track': { backgroundColor: t.accent },
      },
    },
  },
  // ── Tooltip / Dialog / Popover / Menu ─────────────────────────────────────
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
  MuiDialog: {
    styleOverrides: {
      paper: {
        borderRadius: 16,
        border: `1px solid ${t.border}`,
        boxShadow: '0 16px 40px rgba(0,0,0,.55)',
      },
    },
  },
  MuiPopover: {
    styleOverrides: {
      paper: {
        borderRadius: 12,
        border: `1px solid ${t.border}`,
        boxShadow: `0 8px 24px ${t.canvas === '#ffffff' ? 'rgba(15,23,42,.10)' : 'rgba(0,0,0,.50)'}`,
      },
    },
  },
  MuiMenu: {
    styleOverrides: {
      paper: {
        borderRadius: 12,
        border: `1px solid ${t.border}`,
        boxShadow: `0 8px 24px ${t.canvas === '#ffffff' ? 'rgba(15,23,42,.10)' : 'rgba(0,0,0,.50)'}`,
      },
      list: { padding: '4px' },
    },
  },
  MuiMenuItem: {
    styleOverrides: {
      root: {
        fontSize: '0.875rem',
        borderRadius: 8,
        '&:hover': { backgroundColor: t.surface3 },
        '&$selected': { backgroundColor: t.surface3, fontWeight: 600 },
        '&$selected:hover': { backgroundColor: t.surface3 },
      },
    },
  },
  MuiBackdrop: {
    styleOverrides: { root: { backgroundColor: 'rgba(0,0,0,.45)' } },
  },
  // ── Tabs ───────────────────────────────────────────────────────────────────
  MuiTabs: {
    styleOverrides: {
      root: { borderBottom: `1px solid ${t.borderSubtle}`, minHeight: 44 },
      indicator: { backgroundColor: t.accent, height: 2 },
    },
  },
  MuiTab: {
    styleOverrides: {
      root: {
        textTransform: 'none',
        fontWeight: 600,
        letterSpacing: 0,
        minHeight: 44,
        fontSize: '0.875rem',
        color: t.textMuted,
        '&$selected': { color: t.textPrimary },
      },
    },
  },
  // ── Table ──────────────────────────────────────────────────────────────────
  MuiTableRow: {
    styleOverrides: {
      root: {
        '&:hover': { backgroundColor: t.surface1 },
        '&$hover:hover': { backgroundColor: t.surface1 },
      },
    },
  },
  MuiTableCell: {
    styleOverrides: {
      root: {
        borderBottom: `1px solid ${t.borderSubtle}`,
        fontSize: '0.875rem',
        padding: '12px 16px',
      },
      head: {
        fontWeight: 600,
        fontSize: '0.8125rem',
        color: t.textMuted,
        textTransform: 'none',
        letterSpacing: 0,
        backgroundColor: t.canvas,
        borderBottom: `1px solid ${t.border}`,
      },
    },
  },
  // ── List (sidebar nav, settings) ──────────────────────────────────────────
  MuiListItem: {
    styleOverrides: {
      root: {
        borderRadius: 8,
        '&:hover': { backgroundColor: t.surface3 },
        '&$selected': { backgroundColor: t.surface3, color: t.textPrimary },
        '&$selected:hover': { backgroundColor: t.surface3 },
      },
      button: { '&:hover': { backgroundColor: t.surface3 } },
    },
  },
  MuiListItemText: {
    styleOverrides: {
      primary: { fontSize: '0.9375rem', fontWeight: 500 },
      secondary: { fontSize: '0.8125rem', color: t.textMuted },
    },
  },
  // ── Alert banners ─────────────────────────────────────────────────────────
  MuiAlert: {
    styleOverrides: {
      root: {
        borderRadius: 12,
        border: '1px solid',
        fontSize: '0.875rem',
        alignItems: 'flex-start',
      },
      standardError: {
        backgroundColor: states.red.bg,
        borderColor: states.red.edge,
        color: states.red.ink,
        '& .MuiAlert-icon': { color: states.red.ink },
      },
      standardWarning: {
        backgroundColor: states.needs.bg,
        borderColor: states.needs.edge,
        color: states.needs.ink,
        '& .MuiAlert-icon': { color: states.needs.ink },
      },
      standardInfo: {
        backgroundColor: states.running.bg,
        borderColor: states.running.edge,
        color: states.running.ink,
        '& .MuiAlert-icon': { color: states.running.ink },
      },
      standardSuccess: {
        backgroundColor: states.good.bg,
        borderColor: states.good.edge,
        color: states.good.ink,
        '& .MuiAlert-icon': { color: states.good.ink },
      },
    },
  },
  // ── Scaffolder step form ───────────────────────────────────────────────────
  MuiStepper: {
    styleOverrides: { root: { backgroundColor: 'transparent', padding: '16px 0' } },
  },
  MuiStepLabel: {
    styleOverrides: {
      label: {
        fontSize: '0.875rem',
        fontWeight: 500,
        color: t.textMuted,
        '&$active': { fontWeight: 600, color: t.textPrimary },
        '&$completed': { fontWeight: 600, color: t.textSecondary },
      },
    },
  },
  MuiStepIcon: {
    styleOverrides: {
      root: {
        color: t.border,
        '&$active': { color: t.accent },
        '&$completed': { color: t.accent },
      },
      text: { fontSize: '0.75rem', fontWeight: 700, fill: t.inkOnAccent },
    },
  },
  // ── Progress / loading ─────────────────────────────────────────────────────
  MuiLinearProgress: {
    styleOverrides: {
      root: { borderRadius: 4, backgroundColor: t.surface3, height: 4 },
      bar: { backgroundColor: t.accent, borderRadius: 4 },
    },
  },
  MuiCircularProgress: {
    styleOverrides: { root: { color: t.accent } },
  },
  MuiSkeleton: {
    styleOverrides: { root: { backgroundColor: t.surface3 } },
  },
  // ── Accordion (entity/settings sections) ──────────────────────────────────
  MuiAccordion: {
    styleOverrides: {
      root: {
        backgroundColor: t.surface1,
        border: `1px solid ${t.border}`,
        borderRadius: '12px !important',
        boxShadow: 'none',
        '&:before': { display: 'none' },
        '&$expanded': { margin: '8px 0' },
      },
    },
  },
  MuiAccordionSummary: {
    styleOverrides: {
      root: {
        fontWeight: 600,
        fontSize: '0.9375rem',
        minHeight: 52,
        '&$expanded': { minHeight: 52 },
      },
      content: { '&$expanded': { margin: '12px 0' } },
    },
  },
  // ── Misc ───────────────────────────────────────────────────────────────────
  MuiDivider: {
    styleOverrides: { root: { borderColor: t.borderSubtle } },
  },
  MuiSnackbarContent: {
    styleOverrides: {
      root: {
        backgroundColor: t.surface2,
        color: t.textPrimary,
        border: `1px solid ${t.border}`,
        borderRadius: 12,
        boxShadow: '0 8px 24px rgba(0,0,0,.35)',
        fontSize: '0.875rem',
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
  components: componentsFor(light, stateLight),
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
  components: componentsFor(dark, stateDark),
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
