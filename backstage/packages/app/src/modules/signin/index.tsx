// Sign-in routing (2026-09-04: local-dev fix so founder can open the portal without a gateway).
//
// TWO MODES — set by app.signIn.provider in app-config, never in code:
//
//   guest      app-config.local.yaml: app.signIn.provider: guest
//              Fully client-side. No backend call. Clicking "Enter" creates a mock
//              identity. Works even when the backend is down.
//
//   oauth2Proxy (default, production)
//              The front door at catalogue.mumchimp.com has already authenticated
//              the person. ProxiedSignInPage exchanges X-Forwarded-* headers for a
//              Backstage session. If headers are absent (direct hit without the
//              gateway), SignInUnavailable shows one sentence + Try again.
//
// idp decision 0003/0007: no second SSO, no password. This file adds no new
// identity layer — it routes between the two providers that already exist.
import { createFrontendModule, configApiRef, useApi } from '@backstage/frontend-plugin-api';
import { SignInPageBlueprint } from '@backstage/plugin-app-react';
import { ProxiedSignInPage, SignInPage } from '@backstage/core-components';
import { Box, Button, Flex, Text } from '@backstage/ui';

// Shown in oauth2Proxy mode when the header exchange fails (direct hit / proxy hiccup).
export const SignInUnavailable = ({ error }: { error?: Error }) => {
  const title = useApi(configApiRef).getOptionalString('app.title') ?? 'Estate';
  return (
    <Flex
      data-testid="signin-unavailable"
      direction="column"
      align="center"
      justify="center"
      style={{ minHeight: '100vh', padding: 24 }}
    >
      <Box style={{ maxWidth: 420, textAlign: 'center' }}>
        <Flex direction="column" align="center" gap="4">
          <Text as="h1" variant="title-large" weight="bold">
            {title}
          </Text>
          <Text variant="body-large" color="secondary">
            Your sign-in did not reach the portal. Open the estate from its
            front door and it signs you in on the way through.
          </Text>
          <Button variant="primary" onPress={() => window.location.reload()}>
            Try again
          </Button>
          {error && (
            <Text variant="body-x-small" color="secondary">
              {error.message}
            </Text>
          )}
        </Flex>
      </Box>
    </Flex>
  );
};

// The loader returns a React component so useApi (a hook) is valid inside it.
const frontDoorSignInPage = SignInPageBlueprint.make({
  params: {
    loader: async () =>
      function SignInRouter(props) {
        // eslint-disable-next-line react-hooks/rules-of-hooks
        const config = useApi(configApiRef);
        const provider = config.getOptionalString('app.signIn.provider');

        if (provider === 'guest') {
          // guest: fully client-side, no backend. Fine when backend is down locally.
          return <SignInPage {...props} provider="guest" />;
        }

        // Production: exchange front-door headers for a Backstage session.
        return (
          <ProxiedSignInPage
            {...props}
            provider="oauth2Proxy"
            ErrorComponent={SignInUnavailable}
          />
        );
      },
  },
});

export const signInModule = createFrontendModule({
  pluginId: 'app',
  extensions: [frontDoorSignInPage],
});
