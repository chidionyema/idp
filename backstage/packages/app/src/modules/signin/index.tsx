// Production: the front door has already signed the person in; this page
// exchanges the door's headers for a Backstage session without showing a guest
// "Enter" button.
//
// Local `yarn start` (NODE_ENV !== production): official Backstage guest
// SignInPage. Live catalogue.mumchimp.com is a production webpack build, so it
// keeps the front-door page.
//
// 2026-10-04, PROVEN IN A REAL BROWSER: production did NOT reach the door. It asked for the
// oauth2Proxy provider, whose /api/auth/oauth2Proxy/refresh is answered by the edge's
// login-forward-auth-api middleware -- oauth2-proxy's /oauth2/auth, which returns 401 unless the
// browser already carries the door's `.mumchimp.com` cookie. The face is deliberately reachable
// WITHOUT that cookie (its /face and /voice assets are public, and the guest lane exists for a
// visitor who skipped the door), so the refresh always 401'd, SignInUnavailable rendered, and its
// guest "Enter" button reloaded the page straight back into the same failing provider. Measured in
// real Chrome at catalogue.mumchimp.com/face: guest/refresh 200, oauth2Proxy/refresh 401, reload,
// forever -- canvases: 0, and zero requests for /face/talkinghead.mjs or /face/estate.glb.
//
// The defect was a contradiction, not a missing header: ProxiedSignInPage asks the door for an
// identity on a page that does not require the door. The fix is to sign in with the provider this
// deployment actually serves -- guest -- which returns a real Backstage token with no door cookie.
// The door still governs ENTRY: `/` and every data path keep login-forward-auth, so a door session
// is still what gets a verified user their identity, and nobody reads the catalogue without one.
// What changes is only which button the SPA presses, and it now presses the one that opens.
import { createFrontendModule } from '@backstage/frontend-plugin-api';
import { SignInPageBlueprint } from '@backstage/plugin-app-react';
import { SignInPage } from '@backstage/core-components';
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
            The portal could not start your session. Reloading usually clears it; if not, open the
            estate from its front door and it signs you in on the way through.
          </Text>
          {/* A browser reload is the retry, and it is safe now: the page no longer asks a
              provider the edge refuses, so a reload re-runs the guest provider (which answers
              200) rather than looping. */}
          <Button variant="primary" onPress={() => window.location.reload()}>
            Try again
          </Button>
          <SignInPage providers={['guest']} onSignInSuccess={() => window.location.reload()} />
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

// ONE provider in every environment: guest. `yarn start` already used it; production now matches,
// because the deployed edge serves /api/auth/guest/refresh (200, a real token) and refuses the
// door's own refresh to a visitor who came straight to the face. SignInUnavailable stays as the
// error component so a genuine failure still reads in the estate's voice, but it is no longer the
// page's whole behaviour -- with one working provider it is the exception, not the loop.
const frontDoorSignInPage = SignInPageBlueprint.make({
  params: {
    loader: async () => props => (
      <SignInPage {...props} providers={['guest']} ErrorComponent={SignInUnavailable} />
    ),
  },
});

// MEASURED 2026-09-18, because this was guessed at twice and both guesses were wrong.
//
// CLAIM 1, WRONG: that the portal was mis-titled "Bytesync" and needed renaming. It is
// deliberate -- docs/decisions/portal-defects-crew612.md: "app.title and organization.name in
// backstage/app-config.yaml read Mumchimp; the portal is the estate portal, not the store. Both
// now read Bytesync." Reverted, and a note is left at the config so it is not "fixed" again.
//
// CLAIM 2, WRONG: that the guest session does not persist, so every visit met the sign-in wall.
// Driven through a real browser:
//
//   first visit  -> the wall, click Enter
//   reload       -> signed in, no wall
//   new tab      -> signed in, no wall
//   localStorage -> ['@backstage/core:SignInPage:provider', 'language', 'sidebarPinState']
//
// The session is already durable under Backstage's own key. An earlier version of this file
// wrote a private `estate.local.guestSession` key to "fix" it -- a mechanism nothing read,
// invented for a problem that does not exist. Deleted.
//
// WHAT IS ACTUALLY TRUE, and what the founder was seeing: `/fleet` sits behind sign-in, so a
// first or signed-out visit renders the WALL, not the board. Verified through Playwright --
// before Enter the body reads "Bytesync | Guest | Enter as a Guest User", after it the board
// renders with 23 session cards and its full nav. Nothing crashed, and no console error was
// raised at any point.
//
// The lesson, worth more than either fix: a curl proves the API answers and says NOTHING about
// what a person sees. This surface can only be verified in a browser. Every claim made about it
// from a terminal this session was wrong.

export const signInModule = createFrontendModule({
  pluginId: 'app',
  extensions: [frontDoorSignInPage],
});
