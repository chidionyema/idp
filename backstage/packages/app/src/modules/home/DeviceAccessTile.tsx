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
import { Button, Flex, Text } from '@backstage/ui';
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

export function DeviceAccessTile() {
  const loaded = useDeviceAccess();

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

  return (
    <Tile title="Device access" testId="device-access" state={access.state}>
      <StateLine access={access} />

      <Text as="span" color="secondary" data-testid="device-sentence">
        {deviceSentence(access)}
      </Text>

      {/* The one button. Only `not_provisioned` has one, and it never prints a command. */}
      {action ? (
        <Button
          variant="primary"
          data-testid="device-authorize"
          // Opens the estate's own device-authorization door, which is the browser flow that
          // delivers the agent key. A link rather than an in-page fetch, because the flow is
          // interactive and belongs to the portal's identity provider, not to this tile.
          // Until that door exists the button is present and inert rather than absent: an
          // absent control reads as "nothing to do here", and the honest message is "this is
          // the one step that is yours, and it is not built yet".
          onClick={undefined}
        >
          {action}
        </Button>
      ) : null}

      {action ? (
        <Text as="span" color="secondary" data-testid="device-no-terminal">
          No terminal required.
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
