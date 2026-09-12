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
};

const RUNNING = new Set(['running', 'paused']);

/** Order the rows: running first, then by how recently the runtime last saw them. A board where
 *  the live sessions are not at the top is a board nobody reads. */
export function order(sessions: Session[]): Session[] {
  return [...sessions].sort((a, b) => {
    const live = Number(RUNNING.has(b.state)) - Number(RUNNING.has(a.state));
    if (live !== 0) return live;
    return String(b.updated_at ?? '').localeCompare(String(a.updated_at ?? ''));
  });
}

export function summarise(envelope: SessionsEnvelope | null | undefined): Board {
  if (!envelope) {
    return {
      state: 'loading',
      summary: 'Reading the fleet…',
      sessions: [],
      unreachable: [],
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

  return { state: 'ready', summary: parts.join(' · '), sessions, unreachable };
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
