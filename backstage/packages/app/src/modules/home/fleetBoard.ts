// The FleetView board, summarised from the backend's session envelope. Pure: the hook feeds it
// the envelope `GET /api/fleetview/sessions` returns, the page draws what it returns, and tests
// prove it on fixtures. Nothing here fetches, and nothing here names a host (LAW 46).
//
// The envelope is deliberately richer than a bare list. A board has three different facts to
// render and only one of them is "here are the sessions":
//
//   available: false          the source could not be read  -> an error the reader can act on
//   available: true, no rows  the estate really has none    -> an empty state, not a failure
//   unreachable: [adapter]    one runtime did not answer    -> a named gap on an otherwise live board
//
// Collapsing any two of those into "no sessions" is how an outage renders as a quiet day, which
// is the failure this estate names everywhere else.

export type Session = {
  session_id: string;
  runtime: string;
  task: string;
  state: 'running' | 'paused' | 'stopped' | 'failed' | 'unknown';
  repo?: string | null;
  step?: number | null;
  updated_at?: string | null;
  trace_url?: string | null;
  spend_usd?: number | null;
  pull_requests?: string[];
  ticket?: string | null;
  capability_class?: string | null;
  capabilities?: string[] | null;
};

export type SessionsEnvelope = {
  available: boolean;
  error?: string | null;
  sessions?: Session[];
  unreachable?: string[];
  generated_at?: string;
};

export type BoardState = 'loading' | 'unavailable' | 'empty' | 'ready';

export type Board = {
  state: BoardState;
  /** The sentence the page shows above the table. Always present, whatever the state. */
  summary: string;
  sessions: Session[];
  /** Adapters that did not answer. Empty is the healthy answer, never undefined. */
  unreachable: string[];
  /** One row per runtime that has ever appeared, alphabetical. A table of 29 claude-code rows and
   *  1 sovereign row reads as "a claude-code board with sovereign somewhere in it" -- this strip
   *  is what makes every fleet equally visible regardless of which one happens to be biggest. */
  byRuntime: RuntimeCount[];
  /** Set only when two or more DIFFERENT runtimes each failed within the same short window. A
   *  2026 orchestration control plane (routing, budget, identity, state) is shared underneath
   *  every runtime; when it breaks, every runtime shows a failure at once and a per-runtime view
   *  reads that as unrelated noise. Naming the correlation is what turns "three unlucky agents"
   *  into "check the shared cause first." */
  correlatedFailure: CorrelatedFailure | null;
};

export type RuntimeCount = {
  runtime: string;
  total: number;
  running: number;
  failed: number;
};

export type CorrelatedFailure = {
  runtimes: string[];
  windowMinutes: number;
};

/** A note left for a session from the FleetView notes mailbox (`fleetview-backend/src/notes.py`).
 *  Delivery is async, not live: nothing reads this into a running process automatically today, for
 *  any runtime -- a person or the session's own next-turn tooling reads it back later. Keyed by
 *  (session_id, runtime), not by claude-code or any one repo, per the founder's own correction
 *  ("we are model agnostic and this is enterprise wide, not repo wide"). */
export type Note = {
  id: number;
  session_id: string;
  runtime: string;
  note: string;
  author: string;
  created_at: string;
  read_at: string | null;
};

const CORRELATION_WINDOW_MINUTES = 15;

// Item #6: a session with no update in this long has gone quiet enough that a human looking at
// the board would ask "is this stuck?" -- longer than the correlated-failure window above (a
// short gap between updates is normal mid-step), short enough that nudging it is still useful.
const STALE_AFTER_MINUTES = 20;

// Mirrors backend/src/signals.py's _SUPPORTED_RUNTIMES: only sovereign has a live signal path
// today. The board must not offer a nudge button that cannot possibly do anything.
export const NUDGEABLE_RUNTIMES = new Set(['sovereign']);

/** A running session the board has not seen an update from in a while -- the one case item #6's
 *  nudge button is for. A session with no `updated_at` is unmeasured, not stale: staleness is a
 *  claim about elapsed time, and there is no elapsed time to measure without a timestamp. */
export function isStale(
  session: Session,
  now: Date = new Date(),
  afterMinutes: number = STALE_AFTER_MINUTES,
): boolean {
  if (session.state !== 'running') return false;
  if (!session.updated_at) return false;
  const ts = Date.parse(session.updated_at);
  if (Number.isNaN(ts)) return false;
  return now.getTime() - ts >= afterMinutes * 60_000;
}

/** Two or more distinct runtimes with a session that failed inside the same short window, or
 *  null when failures (if any) are confined to one runtime -- the ordinary, uncorrelated case. */
export function correlatedFailure(
  sessions: Session[],
  now: Date = new Date(),
  windowMinutes: number = CORRELATION_WINDOW_MINUTES,
): CorrelatedFailure | null {
  const cutoff = now.getTime() - windowMinutes * 60_000;
  const runtimes = new Set<string>();
  for (const s of sessions) {
    if (s.state !== 'failed') continue;
    const ts = s.updated_at ? Date.parse(s.updated_at) : NaN;
    if (!Number.isNaN(ts) && ts >= cutoff) runtimes.add(s.runtime);
  }
  if (runtimes.size < 2) return null;
  return { runtimes: [...runtimes].sort(), windowMinutes };
}

const RUNNING = new Set(['running', 'paused']);

/** Per-runtime counts, alphabetical by runtime so the strip's order never depends on which fleet
 *  happens to have the most sessions today. */
export function runtimeCounts(sessions: Session[]): RuntimeCount[] {
  const byRuntime = new Map<string, RuntimeCount>();
  for (const s of sessions) {
    const row = byRuntime.get(s.runtime) ?? {
      runtime: s.runtime,
      total: 0,
      running: 0,
      failed: 0,
    };
    row.total += 1;
    if (RUNNING.has(s.state)) row.running += 1;
    if (s.state === 'failed') row.failed += 1;
    byRuntime.set(s.runtime, row);
  }
  return [...byRuntime.values()].sort((a, b) => a.runtime.localeCompare(b.runtime));
}

/** Order the rows: running first, then by how recently the runtime last saw them. A board where
 *  the live sessions are not at the top is a board nobody reads. */
export function order(sessions: Session[]): Session[] {
  return [...sessions].sort((a, b) => {
    const live = Number(RUNNING.has(b.state)) - Number(RUNNING.has(a.state));
    if (live !== 0) return live;
    return String(b.updated_at ?? '').localeCompare(String(a.updated_at ?? ''));
  });
}

export function summarise(
  envelope: SessionsEnvelope | null | undefined,
  now: Date = new Date(),
): Board {
  if (!envelope) {
    return {
      state: 'loading',
      summary: 'Reading the fleet…',
      sessions: [],
      unreachable: [],
      byRuntime: [],
      correlatedFailure: null,
    };
  }

  if (!envelope.available) {
    return {
      state: 'unavailable',
      // The reason is carried through verbatim. "The board is unavailable" without the cause is
      // the message that sends someone looking in the wrong place.
      summary: `The fleet could not be read: ${envelope.error ?? 'no reason given'}`,
      sessions: [],
      unreachable: envelope.unreachable ?? [],
      byRuntime: [],
      correlatedFailure: null,
    };
  }

  const sessions = order(envelope.sessions ?? []);
  const unreachable = envelope.unreachable ?? [];

  if (sessions.length === 0) {
    return {
      state: 'empty',
      summary: unreachable.length
        ? `No sessions, and ${unreachable.length} runtime did not answer: ${unreachable.join('; ')}`
        : 'No sessions are running.',
      sessions: [],
      unreachable,
      byRuntime: [],
      correlatedFailure: null,
    };
  }

  const live = sessions.filter(s => RUNNING.has(s.state)).length;
  const parts = [
    live ? `${live} running` : 'none running',
    `${sessions.length} ${sessions.length === 1 ? 'session' : 'sessions'} listed`,
  ];
  if (unreachable.length) {
    // A live board with a silent runtime says so on the same line. The gap is half the truth and
    // the reader needs it before they trust the count.
    parts.push(`${unreachable.length} runtime did not answer: ${unreachable.join('; ')}`);
  }

  return {
    state: 'ready',
    summary: parts.join(' · '),
    sessions,
    unreachable,
    byRuntime: runtimeCounts(sessions),
    correlatedFailure: correlatedFailure(sessions, now),
  };
}

/** One row's cell text for `state`. Kept here rather than in the page so a test can grade it and
 *  so the board and any future table never disagree about how a state reads. */
export function stateLabel(state: Session['state']): string {
  switch (state) {
    case 'running':
      return 'Running';
    case 'paused':
      return 'Paused';
    case 'stopped':
      return 'Stopped';
    case 'failed':
      return 'Failed';
    default:
      // The catalogue knows which ledgers exist; it does not know whether a session is live.
      // "Unknown" is the honest cell and it must not read as healthy.
      return 'Unknown';
  }
}

/** The money cell. Null means not measured, which is not the same as free. */
export function spendLabel(usd: number | null | undefined): string {
  if (usd === null || usd === undefined) return '—';
  return `$${usd.toFixed(2)}`;
}

/** How many pull requests a session opened, as a cell. Empty array is zero, not null. */
export function prLabel(prs: string[] | null | undefined): string {
  const n = (prs ?? []).length;
  if (n === 0) return '—';
  return n === 1 ? '1 PR' : `${n} PRs`;
}

/** The capability badge text. Null means this runtime carries no capability-class concept,
 * not that the session can do anything -- so the badge is absent, never a fabricated label. */
export function capabilityLabel(capabilityClass: string | null | undefined): string | null {
  return capabilityClass ?? null;
}

/** The badge's tooltip: the exact ops the class allows, straight from AGENTS.md's policy
 * table. Empty/undefined renders as no tooltip, never an invented explanation. */
export function capabilityTitle(capabilities: string[] | null | undefined): string | undefined {
  if (!capabilities || capabilities.length === 0) return undefined;
  return capabilities.join(', ');
}
