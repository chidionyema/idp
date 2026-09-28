// Sign-in for the catalogue behind the estate front door.
//
// The door (Traefik ForwardAuth -> oauth2-proxy -> the OCI identity domain) has already
// authenticated the person by the time a request reaches Backstage, and forwards who they
// are as X-Auth-Request-Email / X-Auth-Request-User. This module makes Backstage trust
// those headers instead of showing its own guest "Enter" page (founder, 2026-08-26:
// "asked me to enter as guest and failed with type error").
//
// No User entities exist in the catalog, so the resolver issues the token itself:
// user:default/<local part of the email>, or of the user name when the domain sent no email
// (crew#307: the founder's own account reached here without the email header and the
// resolver threw, which Backstage serves as a 500; the drill user, created by Terraform with
// an email, never did). A request with neither header is refused, never downgraded to guest.
import { createBackendModule } from '@backstage/backend-plugin-api';
import {
  authProvidersExtensionPoint,
  createProxyAuthProviderFactory,
} from '@backstage/plugin-auth-node';
import { oauth2ProxyAuthenticator } from '@backstage/plugin-auth-backend-module-oauth2-proxy-provider';

const EMAIL_HEADER = 'x-auth-request-email';
const USER_HEADER = 'x-auth-request-user';

function entityName(email: string): string {
  // Entity names allow [a-z0-9._-]; the domain's local parts are plain.
  return email
    .split('@')[0]
    .toLowerCase()
    .replace(/[^a-z0-9._-]/g, '-');
}

const frontDoorAuthModule = createBackendModule({
  pluginId: 'auth',
  moduleId: 'front-door',
  register(reg) {
    reg.registerInit({
      deps: { providers: authProvidersExtensionPoint },
      async init({ providers }) {
        providers.registerProvider({
          providerId: 'oauth2Proxy',
          factory: createProxyAuthProviderFactory({
            authenticator: oauth2ProxyAuthenticator,
            profileTransform: async result => {
              const email = result.getHeader(EMAIL_HEADER);
              const user = result.getHeader(USER_HEADER);
              return {
                profile: {
                  email: email ?? undefined,
                  displayName: user ?? email ?? undefined,
                },
              };
            },
            signInResolver: async ({ result }, ctx) => {
              const who = result.getHeader(EMAIL_HEADER) ?? result.getHeader(USER_HEADER);
              if (!who) {
                throw new Error(
                  `front door forwarded neither ${EMAIL_HEADER} nor ${USER_HEADER}; refusing to sign in`,
                );
              }
              const ref = `user:default/${entityName(who)}`;
              return ctx.issueToken({ claims: { sub: ref, ent: [ref] } });
            },
          }),
        });
      },
    });
  },
});

export default frontDoorAuthModule;
