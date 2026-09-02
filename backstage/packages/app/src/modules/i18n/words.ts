// Overlay Backstage's English with words a visitor can operate without a glossary.
// Official i18n, not a fork: TranslationBlueprint + createTranslationMessages
// https://backstage.io/docs/frontend-system/building-plugins/internationalization
import { createTranslationMessages } from '@backstage/frontend-plugin-api';
import { TranslationBlueprint } from '@backstage/plugin-app-react';
import { catalogTranslationRef } from '@backstage/plugin-catalog/alpha';
import { catalogReactTranslationRef } from '@backstage/plugin-catalog-react/alpha';
import { scaffolderTranslationRef } from '@backstage/plugin-scaffolder/alpha';
import { techdocsTranslationRef } from '@backstage/plugin-techdocs/alpha';

export const catalogWords = TranslationBlueprint.make({
  name: 'catalog-en',
  params: {
    resource: createTranslationMessages({
      ref: catalogTranslationRef,
      full: false,
      messages: {
        'indexPage.title': '{{orgName}} catalogue',
        'indexPage.supportButtonContent':
          'Every service, store, team and page we run.',
        'aboutCard.viewTechdocs': 'View the docs',
        'aboutCard.editButtonTitle': 'Edit details',
        'aboutCard.launchTemplate': 'Start from this',
        'aboutCard.descriptionField.value': 'No description yet',
        'aboutCard.ownerField.value': 'No owner yet',
        'aboutCard.domainField.value': 'No company yet',
        'aboutCard.systemField.value': 'No system yet',
        'aboutCard.tagsField.value': 'No tags yet',
        'catalogTable.warningPanelTitle': 'The catalogue could not be read.',
        'entityPage.notFoundMessage':
          'There is no {{kind}} at the {{link}} you opened.',
        'entityNotFound.title': 'This item was not found',
        'entityContextMenu.inspectMenuTitle': 'Look closer',
        'entityLabelsCard.emptyDescription': 'No labels on this item yet.',
        'entityLinksCard.emptyDescription': 'No links on this item yet.',
        'entityLabels.lifecycleLabel': 'Stage',
        'entityLabels.warningPanelTitle': 'This item was not found',
        'dependsOnComponentsCard.emptyMessage': 'This item depends on no app.',
        'dependsOnResourcesCard.emptyMessage':
          'This item depends on no store or machine.',
        'dependencyOfComponentsCard.emptyMessage':
          'Nothing else depends on this item.',
      },
    }),
  },
});

export const reactWords = TranslationBlueprint.make({
  name: 'catalog-react-en',
  params: {
    resource: createTranslationMessages({
      ref: catalogReactTranslationRef,
      full: false,
      messages: {
        'catalogFilter.title': 'Narrow this list',
        'catalogFilter.buttonTitle': 'Narrow this list',
        'entityKindPicker.title': 'What it is',
        'entityLifecyclePicker.title': 'Stage',
        'entityNamespacePicker.title': 'Area',
        'entityProcessingStatusPicker.title': 'Catalogue status',
        'userListPicker.personalFilter.title': 'Yours',
        'userListPicker.orgFilterAllLabel': 'Everything',
        'missingAnnotationEmptyState.title': 'A required note is missing',
        'entityTableColumnTitle.lifecycle': 'Stage',
        'entityTableColumnTitle.namespace': 'Area',
      },
    }),
  },
});

export const scaffolderWords = TranslationBlueprint.make({
  name: 'scaffolder-en',
  params: {
    resource: createTranslationMessages({
      ref: scaffolderTranslationRef,
      full: false,
      messages: {
        'templateListPage.title': 'Create',
        'templateListPage.pageTitle': 'Create',
        'templateListPage.subtitle':
          'Pick a job. The platform does the steps.',
        'templateListPage.contentHeader.registerExistingButtonTitle':
          'Add something that already exists',
        'templateWizardPage.title': 'Create',
        'templateWizardPage.pageTitle': 'Create',
        'templateWizardPage.subtitle':
          'Pick a job. The platform does the steps.',
        'aboutCard.launchTemplate': 'Start',
        'actionsPage.pageTitle': 'Create',
        'actionsPage.title': 'What Create can do',
        'actionsPage.content.emptyState.title': 'Nothing to show yet',
        'actionsPage.content.emptyState.description':
          'There are no jobs installed, or we could not reach them.',
      },
    }),
  },
});

export const docsWords = TranslationBlueprint.make({
  name: 'techdocs-en',
  params: {
    resource: createTranslationMessages({
      ref: techdocsTranslationRef,
      full: false,
      messages: {
        'aboutCard.viewTechdocs': 'View the docs',
        'notFound.title': 'These docs are not here yet',
      },
    }),
  },
});
