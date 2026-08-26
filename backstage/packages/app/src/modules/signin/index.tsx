// The front door has already signed the person in; this page exchanges the door's
// headers for a Backstage session without showing a guest "Enter" button.
import { createFrontendModule } from '@backstage/frontend-plugin-api';
import { SignInPageBlueprint } from '@backstage/plugin-app-react';
import { ProxiedSignInPage } from '@backstage/core-components';

const frontDoorSignInPage = SignInPageBlueprint.make({
  params: {
    loader: async () => props => (
      <ProxiedSignInPage {...props} provider="oauth2Proxy" />
    ),
  },
});

export const signInModule = createFrontendModule({
  pluginId: 'app',
  extensions: [frontDoorSignInPage],
});
