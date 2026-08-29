// The front door has already signed the person in; this page exchanges the door's
// headers for a Backstage session without showing a guest "Enter" button.
//
// When the exchange fails (a direct hit that skipped the door, a proxy hiccup) the
// first frame a visitor sees is this page. It carries the estate's name and one
// sentence, never the vendor's error text (crew#459 audit, 2026-08-29).
import { createFrontendModule } from '@backstage/frontend-plugin-api';
import { SignInPageBlueprint } from '@backstage/plugin-app-react';
import { ProxiedSignInPage } from '@backstage/core-components';
import { configApiRef, useApi } from '@backstage/frontend-plugin-api';
import { Button, Typography, makeStyles } from '@material-ui/core';
import {
  accent,
  accentSoft,
  inkOnAccent,
  inkOnNavy,
  navy,
} from '../theme/tokens';

const useStyles = makeStyles({
  page: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: navy,
    color: inkOnNavy,
    padding: 24,
  },
  card: { maxWidth: 420, textAlign: 'center' },
  mark: {
    width: 56,
    height: 56,
    borderRadius: 14,
    margin: '0 auto 20px',
    background: `linear-gradient(135deg, ${accentSoft} 0%, ${accent} 100%)`,
    color: inkOnAccent,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: 28,
    fontWeight: 700,
  },
  body: { opacity: 0.85, margin: '12px 0 24px' },
  detail: { display: 'block', marginTop: 24, opacity: 0.6, fontSize: 12 },
});

export const SignInUnavailable = ({ error }: { error?: Error }) => {
  const classes = useStyles();
  const title = useApi(configApiRef).getOptionalString('app.title') ?? 'Estate';
  return (
    <div className={classes.page} data-testid="signin-unavailable">
      <div className={classes.card}>
        <div className={classes.mark} aria-hidden="true">
          {title.trim().charAt(0).toUpperCase()}
        </div>
        <Typography variant="h4">{title}</Typography>
        <Typography variant="body1" className={classes.body}>
          Your sign-in did not reach the portal. Open the estate from its front
          door and it signs you in on the way through.
        </Typography>
        <Button
          variant="contained"
          style={{ background: accent, color: inkOnAccent }}
          onClick={() => window.location.reload()}
        >
          Try again
        </Button>
        {error && (
          <Typography component="span" className={classes.detail}>
            {error.message}
          </Typography>
        )}
      </div>
    </div>
  );
};

const frontDoorSignInPage = SignInPageBlueprint.make({
  params: {
    loader: async () => props =>
      (
        <ProxiedSignInPage
          {...props}
          provider="oauth2Proxy"
          ErrorComponent={SignInUnavailable}
        />
      ),
  },
});

export const signInModule = createFrontendModule({
  pluginId: 'app',
  extensions: [frontDoorSignInPage],
});
