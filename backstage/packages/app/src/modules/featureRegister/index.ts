// crew#857: registers the FeatureRegisterField as a scaffolder custom field
// extension, so the "Enable platform feature" template can use
// `ui:field: FeatureRegisterField` instead of a hand-mirrored enum.
import { FormFieldBlueprint, createFormField } from '@backstage/plugin-scaffolder-react/alpha';
import { createFrontendModule } from '@backstage/frontend-plugin-api';
import { FeatureRegisterField } from './FeatureRegisterField';

export const featureRegisterFieldExtension = FormFieldBlueprint.make({
  name: 'feature-register',
  params: {
    field: async () =>
      createFormField({
        name: 'feature-register',
        component: FeatureRegisterField as any,
      }),
  },
});

export const featureRegisterModule = createFrontendModule({
  pluginId: 'scaffolder',
  extensions: [featureRegisterFieldExtension],
});