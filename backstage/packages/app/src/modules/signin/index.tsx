// Production: the front door has already signed the person in; this page
// exchanges the door's headers for a Backstage session without showing a guest
// "Enter" button.
//
// Local `yarn start` (NODE_ENV !== production): official Backstage guest
// SignInPage. Live catalogue.mumchimp.com is a production webpack build, so it
// keeps the front-door page.
//
// When the exchange fails (a direct hit that skipped the door, a proxy hiccup) the
// first frame a visitor sees is this page. It carries the estate's name and one
// sentence, never the vendor's error text (crew#459 audit, 2026-08-29).
import { createFrontendModule } from '@backstage/frontend-plugin-api';
import { SignInPageBlueprint } from '@backstage/plugin-app-react';
import { ProxiedSignInPage, SignInPage } from '@backstage/core-components';
import { configApiRef, useApi } from '@backstage/frontend-plugin-api';
import { Box, Button, Flex, Text } from '@backstage/ui';

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

const frontDoorSignInPage = SignInPageBlueprint.make({
  params: {
    loader: async () => props =>
      process.env.NODE_ENV !== 'production' ? (
        <SignInPage {...props} providers={['guest']} />
      ) : (
        <ProxiedSignInPage
          {...props}
          provider="oauth2Proxy"
          ErrorComponent={SignInUnavailable}
        />
      ),
  },
});

// MEASURED 2026-09-18, because this was guessed at twice and both guesses were wrong.
//
// The claim was that `/fleet` "breaks" because Backstage's guest session does not persist, so
// every visit met the sign-in wall. That is FALSE. Driven through a real browser:
//
//   first visit  -> the wall, click Enter
//   reload       -> signed in, no wall
//   new tab      -> signed in, no wall
//   localStorage -> ['@backstage/core:SignInPage:provider', 'language', 'sidebarPinState']
//
// The guest session is already durable, under Backstage's own key. An earlier version of this
// file wrote a private `estate.local.guestSession` key to "fix" it -- a mechanism nothing read,
// invented to solve a problem that does not exist. It was deleted. What actually made the page
// look broken is recorded in the report for this session:
//
//   * the app was titled "Bytesync" (PR #1077), so the tab named a stranger's product;
//   * `/fleet` is behind sign-in, so a first or signed-out visit renders the WALL, not the
//     board -- which reads as "the page flashed and broke" when nothing had crashed at all.
//
// The lesson is in the report and worth repeating here: a curl proves the API answers, and says
// nothing about what a person sees. This surface can only be verified in a browser.

export const signInModule = createFrontendModule({
  pluginId: 'app',
  extensions: [frontDoorSignInPage],
});
