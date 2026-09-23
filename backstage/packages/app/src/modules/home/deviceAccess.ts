// Device access: the state of THIS device's read-only cluster identity, and the one action it
// needs. Pure functions and the fetch, kept out of the page so the states are gradeable.
//
// Why a tile and not a terminal (founder, 2026-09-18): "asking ceo to bootstrap from command
// line is fatal", and the copy he approved was:
//
//     Device access
//     ● Not provisioned
//       This device cannot read production. Only you can authorize it.
//       [Authorize this device]
//       No terminal required.
//
// What the tile is NOT allowed to do, from that same review: never say "run these two
// commands", never explain the trust circle, never send a renewal to the phone, never hold
// vault credentials, never change the security model, never ask for a repeat of a manual step.
//
// RENEWAL IS NOT A BUTTON HERE. It is a timer (`bin/idp-jit-device-renew`, every 10 minutes).
// The tile reports what that timer has achieved. A manual [Renew] existed in the first draft
// and was removed: it made the CEO the fallback cron job, which is the thing the review
// rejected by name. The button that remains is the ONE decision only the owner can make --
// putting the agent key on a device that has never had one.

/** The four states a reader has to be able to tell apart, and nothing finer. */
export type DeviceState =
  | 'not_provisioned'
  | 'active'
  | 'expiring'
  | 'expired'
  | 'unreadable';

export interface DeviceAccess {
  state: DeviceState;
  /** Always 'read-only' when provisioned; carried so the tile never has to infer it. */
  scope: string | null;
  /** Seconds until the token dies; null when there is no token. */
  expiresIn: number | null;
  /** The ServiceAccount the token speaks as, or null. */
  subject: string | null;
  /** Why it could not be read, when state is 'unreadable'. */
  reason: string | null;
}

/** The dot's colour. Green only when reads genuinely work; amber is a warning, not a pass. */
export function dotColour(state: DeviceState): string {
  switch (state) {
    case 'active':
      return '#3fb950';
    case 'expiring':
      return '#d29922';
    case 'expired':
      return '#d29922';
    case 'not_provisioned':
      return '#8b949e';
    default:
      return '#f85149';
  }
}

/** The one-line state word. Sentence case, no jargon, no script names. */
export function stateWord(state: DeviceState): string {
  switch (state) {
    case 'active':
      return 'Active';
    case 'expiring':
      return 'Expiring';
    case 'expired':
      return 'Expired';
    case 'not_provisioned':
      return 'Not provisioned';
    default:
      return 'Unreadable';
  }
}

/** "43 min" / "2 hr 10 min" / "less than a minute". Never a raw second count. */
export function humanise(seconds: number | null): string {
  if (seconds === null) return '';
  if (seconds <= 0) return 'expired';
  if (seconds < 60) return 'less than a minute';
  const m = Math.floor(seconds / 60);
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60);
  const rest = m % 60;
  return rest === 0 ? `${h} hr` : `${h} hr ${rest} min`;
}

/**
 * The sentence under the state word.
 *
 * Written as one branch per state so a new state cannot inherit another's sentence by
 * accident, and so the tests below can assert the exact copy the review approved.
 */
export function deviceSentence(d: DeviceAccess): string {
  switch (d.state) {
    case 'not_provisioned':
      return 'This device cannot read production. Only you can authorize it.';
    case 'active':
      return `Read-only access, expires in ${humanise(d.expiresIn)}. Renews itself.`;
    case 'expiring':
      return `Read-only access, expires in ${humanise(d.expiresIn)}. Renewing now.`;
    case 'expired':
      return 'Read-only access expired. It renews itself; if it does not, check the log.';
    default:
      return `Could not read this device's access: ${d.reason ?? 'unknown reason'}`;
  }
}

/**
 * What the single button says, or null when there is no button.
 *
 * Only `not_provisioned` has one. Every other state either needs nothing (active) or is
 * being handled by the timer (expiring/expired), and giving those a button would re-make the
 * CEO the mechanism -- which the review rejected.
 */
export function deviceAction(d: DeviceAccess): string | null {
  return d.state === 'not_provisioned' ? 'Authorize this device' : null;
}

/** True when the tile may honestly claim reads work. Used by anything that reads meaning. */
export function canReadProduction(d: DeviceAccess): boolean {
  return d.state === 'active' || d.state === 'expiring';
}

/**
 * Normalise `bin/idp-jit status` into the tile's shape.
 *
 * Deliberately total: any unknown or missing state becomes 'unreadable' carrying the reason,
 * never a default of 'active'. A status surface that guesses in the permissive direction is
 * worse than one that admits it cannot tell.
 */
export function parseStatus(raw: unknown): DeviceAccess {
  if (!raw || typeof raw !== 'object') {
    return { state: 'unreadable', scope: null, expiresIn: null, subject: null, reason: 'no status returned' };
  }
  const r = raw as Record<string, unknown>;
  const known: DeviceState[] = ['not_provisioned', 'active', 'expiring', 'expired'];
  const state = known.includes(r.state as DeviceState)
    ? (r.state as DeviceState)
    : 'unreadable';
  return {
    state,
    scope: typeof r.scope === 'string' ? r.scope : null,
    expiresIn: typeof r.expires_in === 'number' ? r.expires_in : null,
    subject: typeof r.subject === 'string' ? r.subject : null,
    reason: typeof r.error === 'string' ? r.error : (state === 'unreadable' ? String(r.state ?? 'unknown state') : null),
  };
}
