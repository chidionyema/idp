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
  monoFamily,
  phone,
  reducedMotion,
  stateDark,
  stateLight,
  statusDark,
  statusLight,
} from './tokens';
import { buiVars } from './buiVars';

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

const componentsFor = (t: Tone, states: typeof stateDark) => ({
  MuiCssBaseline: {
    styleOverrides: {
      html: {
        WebkitFontSmoothing: 'antialiased',
        MozOsxFontSmoothing: 'grayscale',
      },
      // BUI reads [data-theme-mode]. Override its defaults with the estate palette
      // so Header, Card and Button speak the same colours as the rest of the portal.
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
      header: { padding: '20px 24px 12px' },
      headerTitle: { fontSize: 17, fontWeight: 600, letterSpacing: '-0.01em' },
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
      root: { borderRadius: 12, backgroundColor: t.surface1, minHeight: 44 },
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

  // ------------------------------------------------------------------------------------
  // The vendor's own pages (crew#843, founder 2026-09-04: "all other need serious work").
  //
  // Six of the ten places the sidebar sends a person -- the catalogue, the Kubernetes view,
  // Find, Docs, Create and You -- plus the entity page and the Map are drawn by Backstage's
  // own components, not by anything in modules/home. Forking a plugin to restyle its page
  // is the half-stitched answer: it takes the fork's maintenance for ever and it fixes one
  // page. Every one of those components names itself to the theme, so the estate's scale,
  // spacing and colour reach all of them from here, in one place, and keep reaching them
  // through a plugin upgrade.
  // ------------------------------------------------------------------------------------

  // The title block on a stock page. Same scale as the shell's own page top.
  BackstageContentHeader: {
    styleOverrides: {
      container: { marginBottom: 20, alignItems: 'flex-end' },
      title: {
        fontSize: 24,
        fontWeight: 700,
        letterSpacing: '-0.02em',
        color: t.textPrimary,
      },
      description: { fontSize: 14, color: t.textSecondary, marginTop: 4 },
      leftItemsBox: { minWidth: 0 },
    },
  },

  // The entity page's tab strip: the vendor's is upper-case and widely tracked, which is
  // the single loudest 2020 tell on the most visited page in the portal.
  BackstageHeaderTabs: {
    styleOverrides: {
      tabsWrapper: {
        backgroundColor: t.canvas,
        borderBottom: `1px solid ${t.borderSubtle}`,
        paddingLeft: 24,
        [phone]: { paddingLeft: 16 },
      },
      tabRoot: {
        textTransform: 'none',
        letterSpacing: 0,
        fontSize: 14,
        fontWeight: 600,
        color: t.textMuted,
        minWidth: 0,
        padding: '10px 14px',
        '&:hover': { color: t.textPrimary },
      },
      defaultTab: {
        textTransform: 'none',
        letterSpacing: 0,
        fontSize: 14,
        padding: '10px 14px',
      },
      selected: { color: t.textPrimary },
    },
  },

  // Nothing found, nothing loaded, nothing built yet. The vendor draws a cartoon beside the
  // sentence; the estate draws the sentence and what to do next, inside the same bordered
  // surface every other empty state on the portal uses.
  BackstageEmptyState: {
    styleOverrides: {
      root: {
        backgroundColor: t.surface1,
        border: `1px solid ${t.border}`,
        borderRadius: 16,
        padding: 32,
      },
      imageContainer: { display: 'none' },
      action: { marginTop: 12 },
    },
  },
  BackstageEmptyStateImage: {
    styleOverrides: { generalImg: { display: 'none' } },
  },
  BackstageMissingAnnotationEmptyState: {
    styleOverrides: {
      code: {
        fontFamily: monoFamily,
        fontSize: 12,
        borderRadius: 8,
        backgroundColor: t.surface3,
        border: `1px solid ${t.borderSubtle}`,
      },
    },
  },

  // The catalogue table's own chrome: its toolbar, its head row and its left filter rail.
  BackstageTableToolbar: {
    styleOverrides: {
      root: { padding: 0, minHeight: 0 },
      title: { '& h6': { fontSize: 17, fontWeight: 600, letterSpacing: '-0.01em' } },
      searchField: { minWidth: 220 },
    },
  },
  BackstageTableHeader: {
    styleOverrides: {
      header: {
        backgroundColor: t.canvas,
        color: t.textMuted,
        fontSize: 12,
        fontWeight: 600,
        letterSpacing: 0,
        textTransform: 'none',
        borderTop: 'none',
        borderBottom: `1px solid ${t.border}`,
      },
    },
  },
  BackstageTableFilters: {
    styleOverrides: {
      root: { paddingRight: 24 },
      header: { fontSize: 15, fontWeight: 600, color: t.textPrimary },
      filters: { padding: 0 },
      value: { fontSize: 13, color: t.textSecondary },
    },
  },
  BackstageSelect: {
    styleOverrides: {
      formControl: { width: '100%' },
      formLabel: {
        fontSize: 12,
        fontWeight: 600,
        color: t.textMuted,
        textTransform: 'none',
        letterSpacing: 0,
      },
      root: { fontSize: 14 },
    },
  },

  // The About card on an entity page is a metadata table; it carried the vendor's
  // upper-case keys and a 24px gutter that no other card on the portal uses.
  BackstageMetadataTableTitleCell: {
    styleOverrides: {
      root: {
        color: t.textMuted,
        fontSize: 12,
        fontWeight: 600,
        textTransform: 'none',
        letterSpacing: 0,
        verticalAlign: 'top',
        padding: '8px 16px 8px 0',
        whiteSpace: 'nowrap',
        border: 'none',
      },
    },
  },
  BackstageMetadataTableCell: {
    styleOverrides: {
      root: {
        fontSize: 14,
        color: t.textPrimary,
        padding: '8px 0',
        border: 'none',
      },
    },
  },
  BackstageHeaderIconLinkRow: { styleOverrides: { links: { gap: 20 } } },
  BackstageIconLinkVertical: {
    styleOverrides: {
      link: { color: t.accent, fontWeight: 600 },
      label: { fontSize: 12, textTransform: 'none', letterSpacing: 0 },
      disabled: { color: t.textMuted },
    },
  },

  // Every rendered document in the portal -- a technical document, a report, a README on an
  // entity page -- comes through this one component.
  BackstageMarkdownContent: {
    styleOverrides: {
      markdown: {
        fontSize: 15,
        lineHeight: 1.65,
        color: t.textPrimary,
        '& h1': { fontSize: 28, fontWeight: 700, letterSpacing: '-0.02em' },
        '& h2': { fontSize: 21, fontWeight: 700, letterSpacing: '-0.01em' },
        '& h3': { fontSize: 17, fontWeight: 600 },
        '& a': { color: t.accent },
        '& code': {
          fontFamily: monoFamily,
          fontSize: 13,
          backgroundColor: t.surface3,
          borderRadius: 6,
          padding: '1px 5px',
        },
        '& pre': {
          backgroundColor: t.surface2,
          border: `1px solid ${t.border}`,
          borderRadius: 12,
          padding: 16,
        },
        '& pre code': { backgroundColor: 'transparent', padding: 0 },
        '& blockquote': {
          borderLeft: `3px solid ${t.borderStrong}`,
          color: t.textSecondary,
          margin: 0,
          padding: '2px 0 2px 16px',
        },
        '& table': { borderCollapse: 'collapse', width: '100%' },
        '& th, & td': {
          borderBottom: `1px solid ${t.borderSubtle}`,
          padding: '8px 12px',
          textAlign: 'left',
        },
        '& img': { maxWidth: '100%' },
      },
    },
  },

  // The Map page. Its nodes and edges are SVG, so they take fill and stroke, not colour.
  BackstageDependencyGraphDefaultNode: {
    styleOverrides: {
      node: { fill: t.surface2, stroke: t.borderStrong, strokeWidth: 1 },
      text: { fill: t.textPrimary, fontSize: 13, fontWeight: 600 },
    },
  },
  BackstageDependencyGraphDefaultLabel: {
    styleOverrides: { text: { fill: t.textSecondary, fontSize: 12 } },
  },

  // The Create page's template cards, and the same grid the estate's own tiles use.
  BackstageItemCardGrid: {
    styleOverrides: {
      root: {
        gridTemplateColumns: 'repeat(auto-fill, minmax(min(21rem, 100%), 1fr))',
        gridGap: 16,
      },
    },
  },
  BackstageItemCardHeader: {
    styleOverrides: {
      root: {
        backgroundImage: 'none',
        backgroundColor: t.surface2,
        color: t.textPrimary,
        borderBottom: `1px solid ${t.borderSubtle}`,
        padding: '16px 20px 12px',
      },
    },
  },

  // Something went wrong, said the same way as everywhere else: a tinted panel with a word
  // and a border, never colour on its own.
  BackstageWarningPanel: {
    styleOverrides: {
      panel: {
        backgroundColor: states.needs.bg,
        border: `1px solid ${states.needs.edge}`,
        borderRadius: 12,
        boxShadow: 'none',
      },
      summary: { padding: '8px 16px' },
      summaryText: { color: states.needs.ink, fontWeight: 600 },
      message: { backgroundColor: 'transparent' },
    },
  },
  BackstageGauge: {
    styleOverrides: {
      description: { fontSize: 12, color: t.textSecondary },
      colorUnknown: { stroke: t.borderStrong },
    },
  },
  BackstageBottomLink: {
    styleOverrides: {
      root: { borderTop: `1px solid ${t.borderSubtle}` },
      boxTitle: { fontSize: 14, fontWeight: 600, color: t.accent },
    },
  },

  // The Material components those pages are built out of. A stock table is where the age
  // shows most: tight rows, a heavy divider under every one, and no hover.
  MuiTableCell: {
    styleOverrides: {
      root: {
        borderBottom: `1px solid ${t.borderSubtle}`,
        padding: '12px 16px',
        fontSize: 14,
      },
      head: { fontSize: 12, fontWeight: 600, color: t.textMuted },
    },
  },
  MuiTableRow: {
    styleOverrides: {
      root: { '&:hover': { backgroundColor: t.surface3 } },
      head: { '&:hover': { backgroundColor: 'transparent' } },
    },
  },
  MuiTablePagination: {
    styleOverrides: {
      root: { borderTop: `1px solid ${t.borderSubtle}`, fontSize: 13 },
      toolbar: { minHeight: 48 },
    },
  },
  MuiAccordion: {
    styleOverrides: {
      root: {
        border: `1px solid ${t.border}`,
        borderRadius: 12,
        boxShadow: 'none',
        '&:before': { display: 'none' },
        '& + &': { marginTop: 8 },
      },
    },
  },
  MuiAccordionSummary: {
    styleOverrides: {
      root: { minHeight: 48, padding: '0 16px' },
      content: { margin: '10px 0' },
    },
  },
  MuiCardHeader: {
    styleOverrides: {
      title: { fontSize: 17, fontWeight: 600, letterSpacing: '-0.01em' },
      subheader: { fontSize: 13, color: t.textSecondary },
    },
  },
  MuiDivider: { styleOverrides: { root: { backgroundColor: t.borderSubtle } } },
  MuiLinearProgress: {
    styleOverrides: {
      root: { height: 4, borderRadius: 999, backgroundColor: t.surface3 },
    },
  },
  MuiAvatar: {
    styleOverrides: {
      root: { backgroundColor: t.surface3, color: t.textSecondary },
    },
  },
  MuiBreadcrumbs: {
    styleOverrides: { root: { fontSize: 13, color: t.textMuted } },
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
