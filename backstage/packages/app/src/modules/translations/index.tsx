// Plain-English copy overrides (founder 2026-09-04: "better language, more intuitive").
// Architecture: translations in Backstage's alpha frontend system flow through
// TranslationBlueprint → TranslationsApi (plugin-app) → I18nextTranslationApi.
// We use createTranslationMessages (synchronous, no async loader) because these are
// app-level overrides that are always present, not lazily loaded locale files.
// Each override is wrapped in a TranslationBlueprint extension, then bundled into a
// single FrontendModule registered in App.tsx, so no plugin source is forked.
import {
  createFrontendModule,
  createTranslationMessages,
} from '@backstage/frontend-plugin-api';
import { TranslationBlueprint } from '@backstage/plugin-app-react';
import { catalogTranslationRef } from '@backstage/plugin-catalog';
import { userSettingsTranslationRef } from '@backstage/plugin-user-settings';
import { searchReactTranslationRef } from '@backstage/plugin-search-react';

// ── Catalog ──────────────────────────────────────────────────────────────────
const catalogEnMessages = createTranslationMessages({
  ref: catalogTranslationRef,
  messages: {
    indexPage: {
      title: '{{orgName}} — what we run',
      createButtonTitle: 'Add something',
      supportButtonContent: 'Every service, tool and system the estate runs',
    },
    entityPage: {
      notFoundMessage:
        'Nothing here matches {{kind}} / {{link}}. It may have been removed.',
      notFoundLinkText: 'name and namespace',
    },
    aboutCard: {
      title: 'About',
      refreshButtonTitle: 'Re-read from source',
      editButtonTitle: 'Edit the YAML',
      editButtonAriaLabel: 'Edit',
      createSimilarButtonTitle: 'Create a similar one',
      refreshScheduledMessage: 'Syncing now',
      refreshButtonAriaLabel: 'Refresh',
      launchTemplate: 'Start from this template',
      viewTechdocs: 'Read the docs',
      viewSource: 'Open source',
      unknown: 'not set',
      descriptionField: { label: 'Description', value: 'No description yet' },
      ownerField: { label: 'Owner', value: 'No owner assigned' },
      domainField: { label: 'Domain', value: 'None' },
      systemField: { label: 'System', value: 'None' },
      parentComponentField: { label: 'Part of', value: 'None' },
      kindField: { label: 'Kind' },
      typeField: { label: 'Type' },
      lifecycleField: { label: 'Lifecycle' },
      tagsField: { label: 'Tags', value: 'No tags' },
      targetsField: { label: 'Targets' },
    },
    searchResultItem: {
      kind: 'Kind',
      type: 'Type',
      lifecycle: 'Lifecycle',
      owner: 'Owner',
    },
    catalogTable: {
      warningPanelTitle: 'Could not load the service list.',
      viewActionTitle: 'Open',
      editActionTitle: 'Edit',
      starActionTitle: 'Bookmark',
      unStarActionTitle: 'Remove bookmark',
      allFilters: 'All',
    },
    dependencyOfComponentsCard: {
      title: 'Used by',
      emptyMessage: 'Nothing depends on this yet.',
    },
    dependsOnComponentsCard: {
      title: 'Depends on',
      emptyMessage: 'No dependencies declared.',
    },
    dependsOnResourcesCard: {
      title: 'Needs resources',
      emptyMessage: 'No resource dependencies declared.',
    },
    entityContextMenu: {
      copiedMessage: 'Copied',
      moreButtonTitle: 'More',
      inspectMenuTitle: 'Inspect raw entity',
      copyURLMenuTitle: 'Copy link',
      unregisterMenuTitle: 'Remove from catalog',
      moreButtonAriaLabel: 'More actions',
    },
    entityLabelsCard: {
      title: 'Labels',
      columnKeyLabel: 'Label',
    },
  },
});

const catalogExtension = TranslationBlueprint.make({
  name: 'catalog-en',
  params: { resource: catalogEnMessages },
});

// ── User Settings ─────────────────────────────────────────────────────────────
const settingsEnMessages = createTranslationMessages({
  ref: userSettingsTranslationRef,
  messages: {
    languageToggle: {
      title: 'Language',
      description: 'Switch the display language',
      select: 'Select language {{language}}',
    },
    themeToggle: {
      title: 'Appearance',
      description: 'Switch between light and dark mode',
      select: 'Select {{theme}}',
      selectAuto: 'Match the system theme',
      names: { light: 'Light', dark: 'Dark', auto: 'System default' },
    },
    signOutMenu: { title: 'Sign out', moreIconTitle: 'More' },
    pinToggle: {
      title: 'Keep the nav open',
      description: 'Show nav labels without hovering',
      switchTitles: { unpin: 'Collapse nav', pin: 'Keep nav open' },
      ariaLabelTitle: 'Keep nav open',
    },
    identityCard: {
      title: 'Your account',
      noIdentityTitle: 'Not signed in',
      userEntity: 'Your catalog entry',
      ownershipEntities: 'What you own',
    },
    defaultProviderSettings: {
      description: 'Lets you sign in with {{provider}}',
    },
    emptyProviders: {
      title: 'No sign-in providers',
      description:
        'Add a provider in app-config.yaml to enable additional sign-in methods.',
      action: {
        title: 'Add to app-config.yaml:',
        readMoreButtonTitle: 'Read the docs',
      },
    },
    providerSettingsItem: {
      title: { signIn: 'Sign in with {{title}}', signOut: 'Sign out of {{title}}' },
      buttonTitle: { signIn: 'Sign in', signOut: 'Sign out' },
    },
    authProviders: { title: 'Sign-in providers' },
    defaultSettingsPage: {
      tabsTitle: {
        general: 'General',
        authProviders: 'Sign-in',
        featureFlags: 'Feature flags',
      },
    },
    featureFlags: {
      title: 'Feature flags',
      description: 'Refresh the page after changing a flag',
      emptyFlags: {
        title: 'No flags registered',
        description: 'Plugins register feature flags so individual users can opt in.',
        action: {
          title: 'Register a flag in your plugin:',
          readMoreButtonTitle: 'Read the docs',
        },
      },
      filterTitle: 'Filter',
      clearFilter: 'Clear',
      flagItem: {
        title: { disable: 'Off', enable: 'On' },
        subtitle: {
          registeredInApplication: 'Registered in the application',
          registeredInPlugin: 'Registered in {{pluginId}}',
        },
      },
    },
    settingsLayout: { title: 'Your settings' },
    sidebarTitle: 'Settings',
    profileCard: { title: 'Profile' },
    appearanceCard: { title: 'Appearance' },
  },
});

const settingsExtension = TranslationBlueprint.make({
  name: 'user-settings-en',
  params: { resource: settingsEnMessages },
});

// ── Search ────────────────────────────────────────────────────────────────────
const searchEnMessages = createTranslationMessages({
  ref: searchReactTranslationRef,
  messages: {
    searchBar: {
      title: 'Search',
      placeholder: 'Search everything in the estate',
    },
    noResultsDescription: 'Nothing matched. Try fewer words.',
  },
});

const searchExtension = TranslationBlueprint.make({
  name: 'search-react-en',
  params: { resource: searchEnMessages },
});

// ── Module (registered in App.tsx) ────────────────────────────────────────────
export const translationsModule = createFrontendModule({
  pluginId: 'app',
  extensions: [catalogExtension, settingsExtension, searchExtension],
});
