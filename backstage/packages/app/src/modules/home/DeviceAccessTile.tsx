// The Device access tile: this device's read-only cluster identity, in one glance, with the
// one action only the owner can take.
//
// The copy is fixed by the founder's review (2026-09-18), and the tests assert it verbatim:
//
//     Device access
//     ● Not provisioned
//       This device cannot read production. Only you can authorize it.
//       [Authorize this device]
//       No terminal required.
//
// What this tile must never do, all from that review:
//   * never say "run these two commands" -- no terminal, ever
//   * never explain the trust circle -- the reader does not need the architecture
//   * never send a renewal to the phone -- "you need to tap your phone to renew" is rejected
//   * never hold vault credentials or change the security model
//   * never ask for a repeat of a manual step -- "the CEO is not a cron job"
//
// Which is why there is no [Renew] here. Renewal is `bin/idp-jit-device-renew` on a ten-minute
// timer; the tile reports what the timer achieved. The single button that remains is the one
// decision that cannot be a timer: putting the agent key on a device that has never had one.
//
// AND WHY THE BUTTON IS A LOCAL HANDOFF, NOT A BROWSER FLOW (founder's ruling, 2026-09-18):
// "Keep key delivery out of the portal... guided local handoff." The portal's strongest
// property is that it holds no vault credentials and never sees the key or the token. This
// component opens `idp-device://`, which only something installed on this machine can handle,
// and the device's own helper performs the delivery. The portal passes a nonce and nothing
// else -- `handoff.py` enforces that on the server side, and its tests assert it.
//
// WHEN NO HELPER IS INSTALLED the button degrades to a guided link, per the ruling: "not a
// terminal tutorial". The reader gets a one-line instruction and a copyable link, not a shell.
import { useState } from 'react';
import { Button, Flex, Text } from '@backstage/ui';
import { configApiRef, useApi, fetchApiRef } from '@backstage/frontend-plugin-api';
import { Tile } from '../shell';
import { useDeviceAccess } from './useDeviceAccess';
import {
  DeviceAccess,
  canReadProduction,
  deviceAction,
  deviceSentence,
  dotColour,
  stateWord,
} from './deviceAccess';

/** The dot plus the state word. One dot, one word, no icon set, no colour alone. */
function StateLine({ access }: { access: DeviceAccess }) {
  return (
    <Flex align="center" gap="2">
      <span
        aria-hidden="true"
        data-testid="device-dot"
        style={{
          display: 'inline-block',
          width: 8,
          height: 8,
          borderRadius: '50%',
          background: dotColour(access.state),
          flexShrink: 0,
        }}
      />
      <Text as="span" weight="bold" data-testid="device-state">
        {stateWord(access.state)}
      </Text>
      {canReadProduction(access) && access.scope ? (
        <Text as="span" color="secondary" data-testid="device-scope">
          · {access.scope}
        </Text>
      ) : null}
    </Flex>
  );
}

/** Where the browser sends the handoff request. Same door as every other portal read. */
export const AUTHORIZE_PATH = 'plugin://proxy/fleetview/device-authorize';

/**
 * The guided fallback, shown when the browser could not open the local helper.
 *
 * Per the ruling this is "a clear 'install/run this helper' step, not a terminal tutorial":
 * one instruction, one link, no shell, no command list.
 */
function GuidedFallback({ url, onRetry }: { url: string; onRetry: () => void }) {
  return (
    <Flex direction="column" gap="2">
      <Text as="span" color="secondary" data-testid="device-guided">
        This browser could not open the device helper. Install it once and this button will
        work from then on.
      </Text>
      <Flex align="center" gap="2">
        <Button variant="secondary" data-testid="device-opens-link" onPress={() => window.open(url, '_self')}>
          Open the helper
        </Button>
        <Button variant="secondary" data-testid="device-retry" onPress={onRetry}>
          Try again
        </Button>
      </Flex>
    </Flex>
  );
}

export function DeviceAccessTile() {
  const loaded = useDeviceAccess();
  const fetchApi = useApi(fetchApiRef);
  const configApi = useApi(configApiRef);
  const [handoff, setHandoff] = useState<{ url: string | null; error: string | null }>({
    url: null,
    error: null,
  });

  if (loaded.state === 'loading') {
    return (
      <Tile title="Device access" testId="device-access">
        <Text as="span" color="secondary">
          Checking…
        </Text>
      </Tile>
    );
  }

  const access = loaded.access;
  const action = deviceAction(access);

  /**
   * Ask the portal for a challenge, then open the local handoff.
   *
   * The portal mints a nonce and returns a URL; it never returns a key. If the browser cannot
   * route the custom scheme -- which is what happens when the helper is not installed -- the
   * URL is kept and the guided fallback renders, so the reader is never left with a dead
   * button and no next step.
   */
  const authorize = async () => {
    setHandoff({ url: null, error: null });
    try {
      const res = await fetchApi.fetch(AUTHORIZE_PATH, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      const body = (await res.json()) as { url?: string; error?: string };
      if (!res.ok || !body.url) {
        setHandoff({ url: null, error: body.error ?? `the portal answered ${res.status}` });
        return;
      }
      setHandoff({ url: body.url, error: null });
      // A custom scheme in a same-tab navigation is the standard way a page hands off to a
      // local app; the browser stays put if nothing is registered, which is the case the
      // guided fallback below handles.
      window.location.href = body.url;
    } catch (err) {
      setHandoff({
        url: null,
        error: err instanceof Error ? err.message : String(err),
      });
    }
  };

  // The helper's own path, shown only in the guided fallback so a reader can find it.
  const helperHint =
    (configApi.getOptionalString('estate.deviceHelperPath') ?? 'bin/idp-device-authorize');

  return (
    <Tile title="Device access" testId="device-access" state={access.state}>
      <StateLine access={access} />

      <Text as="span" color="secondary" data-testid="device-sentence">
        {deviceSentence(access)}
      </Text>

      {/* The one button. Only `not_provisioned` has one, and it never prints a command. */}
      {action ? (
        <Button variant="primary" data-testid="device-authorize" onPress={() => void authorize()}>
          {action}
        </Button>
      ) : null}

      {action && !handoff.url ? (
        <Text as="span" color="secondary" data-testid="device-no-terminal">
          No terminal required.
        </Text>
      ) : null}

      {action && handoff.url ? (
        <GuidedFallback url={handoff.url} onRetry={() => void authorize()} />
      ) : null}

      {action && handoff.error ? (
        <Text as="span" color="danger" data-testid="device-error">
          {handoff.error} — the helper is {helperHint}
        </Text>
      ) : null}

      {/* When reads work, say what they let you do, once, quietly. */}
      {canReadProduction(access) && access.subject ? (
        <Text as="span" color="secondary" data-testid="device-subject">
          {access.subject}
        </Text>
      ) : null}
    </Tile>
  );
}
