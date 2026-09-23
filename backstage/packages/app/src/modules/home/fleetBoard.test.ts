import {
  attentionReason,
  capabilityLabel,
  capabilityTitle,
  correlatedFailure,
  isStale,
  needsAttention,
  NUDGEABLE_RUNTIMES,
  order,
  prLabel,
  runtimeCounts,
  spendLabel,
  stateLabel,
  summarise,
  timelineFor,
} from './fleetBoard';
import type { Note, Signal } from './fleetBoard';
import type { Session } from './fleetBoard';

const session = (over: Partial<Session> = {}): Session => ({
  session_id: 'sb-1',
  runtime: 'sovereign',
  task: 'fix the board',
  state: 'running',
  repo: 'idp',
  step: 3,
  updated_at: '2026-09-12T10:00:00Z',
  trace_url: null,
  spend_usd: null,
  pull_requests: [],
  ticket: null,
  ...over,
});

describe('the board tells three different facts apart', () => {
  it('a source that could not be read is unavailable, not empty', () => {
    const board = summarise({
      available: false,
      error: 'FileNotFoundError: catalogue not readable',
    });
    expect(board.state).toBe('unavailable');
    // The cause travels with the verdict. "Unavailable" alone sends the reader looking in the
    // wrong place.
    expect(board.summary).toContain('catalogue not readable');
    expect(board.sessions).toEqual([]);
  });

  it('a source with no sessions is empty, and says so without an error', () => {
    const board = summarise({ available: true, sessions: [], unreachable: [] });
    expect(board.state).toBe('empty');
    expect(board.summary).toBe('No sessions are running.');
  });

  it('a live board with one silent runtime names the gap', () => {
    const board = summarise({
      available: true,
      sessions: [session()],
      unreachable: ['sovereign: RuntimeError: refused'],
    });
    expect(board.state).toBe('ready');
    // The count is half the truth: the reader must know a runtime did not answer before they
    // trust "1 running".
    expect(board.summary).toContain('1 running');
    expect(board.summary).toContain('did not answer');
    expect(board.unreachable).toEqual(['sovereign: RuntimeError: refused']);
  });

  it('nothing has arrived yet is loading, not empty', () => {
    expect(summarise(null).state).toBe('loading');
  });
});

describe('the door updates itself without inventing a state', () => {
  it('a session whose runtime did not say reads Unknown, never Running', () => {
    // The catalogue knows which ledgers exist and nothing about whether they are live. A board
    // that guessed "Running" here shows a green row for a session that ended last week.
    const board = summarise({
      available: true,
      sessions: [session({ state: 'unknown' })],
      unreachable: [],
    });
    expect(board.sessions[0].state).toBe('unknown');
    expect(stateLabel(board.sessions[0].state)).toBe('Unknown');
    expect(board.summary).toContain('none running');
  });
});

describe('ordering', () => {
  it('running sessions come first, then the most recent', () => {
    const rows = order([
      session({ session_id: 'old', state: 'stopped', updated_at: '2026-09-01T00:00:00Z' }),
      session({ session_id: 'live', state: 'running', updated_at: '2026-08-01T00:00:00Z' }),
      session({ session_id: 'recent-stop', state: 'stopped', updated_at: '2026-09-11T00:00:00Z' }),
    ]);
    // A board where the live sessions are not at the top is a board nobody reads, even when the
    // rows are all correct.
    expect(rows.map(r => r.session_id)).toEqual(['live', 'recent-stop', 'old']);
  });

  it('a paused session counts as live', () => {
    const rows = order([
      session({ session_id: 'stopped', state: 'stopped' }),
      session({ session_id: 'paused', state: 'paused' }),
    ]);
    expect(rows[0].session_id).toBe('paused');
  });
});

describe('every fleet is equally visible, not just the biggest', () => {
  it('a runtime with one session counts the same as one with many', () => {
    const rows = runtimeCounts([
      session({ session_id: 'a', runtime: 'claude-code', state: 'running' }),
      session({ session_id: 'b', runtime: 'claude-code', state: 'stopped' }),
      session({ session_id: 'c', runtime: 'sovereign', state: 'failed' }),
    ]);
    // Alphabetical, so the strip's order never depends on which fleet happens to be biggest today.
    expect(rows).toEqual([
      { runtime: 'claude-code', total: 2, running: 1, failed: 0 },
      { runtime: 'sovereign', total: 1, running: 0, failed: 1 },
    ]);
  });

  it('a board with no sessions has no runtime rows', () => {
    expect(summarise({ available: true, sessions: [], unreachable: [] }).byRuntime).toEqual([]);
  });

  it('a ready board carries a row per runtime actually present', () => {
    const board = summarise({
      available: true,
      sessions: [session({ runtime: 'pi' }), session({ session_id: 'g', runtime: 'gemini' })],
      unreachable: [],
    });
    expect(board.byRuntime.map(r => r.runtime)).toEqual(['gemini', 'pi']);
  });
});

describe('a shared cause looks different from bad luck', () => {
  const NOW = new Date('2026-09-15T10:00:00Z');

  it('one runtime failing alone is not a correlated failure', () => {
    const result = correlatedFailure(
      [session({ runtime: 'sovereign', state: 'failed', updated_at: '2026-09-15T09:55:00Z' })],
      NOW,
    );
    expect(result).toBeNull();
  });

  it('two different runtimes failing in the same window is named, not silent', () => {
    const result = correlatedFailure(
      [
        session({ session_id: 'a', runtime: 'sovereign', state: 'failed', updated_at: '2026-09-15T09:55:00Z' }),
        session({ session_id: 'b', runtime: 'claude-code', state: 'failed', updated_at: '2026-09-15T09:50:00Z' }),
      ],
      NOW,
    );
    expect(result).toEqual({ runtimes: ['claude-code', 'sovereign'], windowMinutes: 15 });
  });

  it('the same runtime failing twice does not count as correlated', () => {
    const result = correlatedFailure(
      [
        session({ session_id: 'a', runtime: 'sovereign', state: 'failed', updated_at: '2026-09-15T09:55:00Z' }),
        session({ session_id: 'b', runtime: 'sovereign', state: 'failed', updated_at: '2026-09-15T09:50:00Z' }),
      ],
      NOW,
    );
    expect(result).toBeNull();
  });

  it('a failure outside the window does not count', () => {
    const result = correlatedFailure(
      [
        session({ session_id: 'a', runtime: 'sovereign', state: 'failed', updated_at: '2026-09-15T09:55:00Z' }),
        session({ session_id: 'b', runtime: 'claude-code', state: 'failed', updated_at: '2026-09-15T08:00:00Z' }),
      ],
      NOW,
    );
    expect(result).toBeNull();
  });

  it('a ready board carries the correlation when it is real', () => {
    const board = summarise(
      {
        available: true,
        sessions: [
          session({ session_id: 'a', runtime: 'sovereign', state: 'failed', updated_at: '2026-09-15T09:55:00Z' }),
          session({ session_id: 'b', runtime: 'claude-code', state: 'failed', updated_at: '2026-09-15T09:50:00Z' }),
        ],
        unreachable: [],
      },
      NOW,
    );
    expect(board.correlatedFailure).toEqual({ runtimes: ['claude-code', 'sovereign'], windowMinutes: 15 });
  });

  it('loading, unavailable and empty boards never carry a correlation', () => {
    expect(summarise(null).correlatedFailure).toBeNull();
    expect(summarise({ available: false, error: 'x' }).correlatedFailure).toBeNull();
    expect(summarise({ available: true, sessions: [], unreachable: [] }).correlatedFailure).toBeNull();
  });
});

describe('cells that must not flatter', () => {
  it('an unmeasured spend is a dash, not zero', () => {
    // Zero is a measurement. A dash is the absence of one, and the reader can tell them apart.
    expect(spendLabel(null)).toBe('—');
    expect(spendLabel(undefined)).toBe('—');
    expect(spendLabel(0)).toBe('$0.00');
    expect(spendLabel(12.5)).toBe('$12.50');
  });

  it('no pull requests is a dash, one is 1 PR', () => {
    expect(prLabel([])).toBe('—');
    expect(prLabel(null)).toBe('—');
    expect(prLabel(['https://github.com/x/y/pull/1'])).toBe('1 PR');
    expect(prLabel(['a', 'b'])).toBe('2 PRs');
  });

  it('a capability class with no runtime concept of one is absent, not a fabricated label', () => {
    expect(capabilityLabel(null)).toBeNull();
    expect(capabilityLabel(undefined)).toBeNull();
    expect(capabilityLabel('engine')).toBe('engine');
  });

  it('the capability tooltip names the exact allowed ops, or nothing at all', () => {
    expect(capabilityTitle(null)).toBeUndefined();
    expect(capabilityTitle(undefined)).toBeUndefined();
    expect(capabilityTitle([])).toBeUndefined();
    expect(capabilityTitle(['fs_read', 'fs_commit'])).toBe('fs_read, fs_commit');
  });
});

describe('item #6: a stale session is a claim about elapsed time, never a guess', () => {
  const NOW = new Date('2026-09-15T10:00:00Z');

  it('a running session with no update in 20+ minutes is stale', () => {
    expect(
      isStale(session({ state: 'running', updated_at: '2026-09-15T09:39:00Z' }), NOW),
    ).toBe(true);
  });

  it('a running session updated recently is not stale', () => {
    expect(
      isStale(session({ state: 'running', updated_at: '2026-09-15T09:55:00Z' }), NOW),
    ).toBe(false);
  });

  it('a session that is not running is never stale, however old', () => {
    expect(
      isStale(session({ state: 'stopped', updated_at: '2026-01-01T00:00:00Z' }), NOW),
    ).toBe(false);
  });

  it('a session with no updated_at is unmeasured, not stale', () => {
    expect(isStale(session({ state: 'running', updated_at: null }), NOW)).toBe(false);
  });

  it('an unparseable updated_at is unmeasured, not stale', () => {
    expect(isStale(session({ state: 'running', updated_at: 'not-a-date' }), NOW)).toBe(false);
  });

  it('sovereign, claude-code, otto, and cyrus all have a live signal path', () => {
    expect(NUDGEABLE_RUNTIMES.has('sovereign')).toBe(true);
    expect(NUDGEABLE_RUNTIMES.has('claude-code')).toBe(true);
    expect(NUDGEABLE_RUNTIMES.has('otto')).toBe(true);
    expect(NUDGEABLE_RUNTIMES.has('cyrus')).toBe(true);
  });
});

describe('needs attention: grouping from real signals only, nothing invented', () => {
  const NOW = new Date('2026-09-15T10:00:00Z');

  it('a failed session needs attention', () => {
    expect(attentionReason(session({ state: 'failed' }), NOW)).toBe('failed');
  });

  it('a stale running session needs attention', () => {
    expect(
      attentionReason(session({ state: 'running', updated_at: '2026-09-15T09:00:00Z' }), NOW),
    ).toBe('stale');
  });

  it('a running, recently-updated session needs nothing', () => {
    expect(
      attentionReason(session({ state: 'running', updated_at: '2026-09-15T09:59:00Z' }), NOW),
    ).toBeNull();
  });

  it('a stopped session needs nothing, however old', () => {
    expect(
      attentionReason(session({ state: 'stopped', updated_at: '2026-01-01T00:00:00Z' }), NOW),
    ).toBeNull();
  });

  it('failed sessions rank ahead of stale ones, each newest first', () => {
    const stale1 = session({
      session_id: 'stale-older',
      state: 'running',
      updated_at: '2026-09-15T09:00:00Z',
    });
    const stale2 = session({
      session_id: 'stale-newer',
      state: 'running',
      updated_at: '2026-09-15T09:20:00Z',
    });
    const failed1 = session({
      session_id: 'failed-older',
      state: 'failed',
      updated_at: '2026-09-15T08:00:00Z',
    });
    const failed2 = session({
      session_id: 'failed-newer',
      state: 'failed',
      updated_at: '2026-09-15T09:30:00Z',
    });
    const healthy = session({ session_id: 'healthy', state: 'running', updated_at: '2026-09-15T09:59:00Z' });
    const result = needsAttention([stale1, healthy, failed1, stale2, failed2], NOW);
    expect(result.map(s => s.session_id)).toEqual([
      'failed-newer',
      'failed-older',
      'stale-newer',
      'stale-older',
    ]);
  });

  it('a ready board carries its own attention list', () => {
    const board = summarise(
      {
        available: true,
        sessions: [session({ session_id: 'ok', state: 'running', updated_at: '2026-09-15T09:59:00Z' }),
          session({ session_id: 'down', state: 'failed', updated_at: '2026-09-15T09:59:00Z' })],
        unreachable: [],
      },
      NOW,
    );
    expect(board.attention.map(s => s.session_id)).toEqual(['down']);
  });

  it('loading, unavailable and empty boards carry no attention', () => {
    expect(summarise(null).attention).toEqual([]);
    expect(summarise({ available: false, error: 'x' }).attention).toEqual([]);
    expect(summarise({ available: true, sessions: [], unreachable: [] }).attention).toEqual([]);
  });
});

describe('timeline: notes and signals merged, nothing synthesized', () => {
  const note = (over: Partial<Note> = {}): Note => ({
    id: 1,
    session_id: 'sb-1',
    runtime: 'sovereign',
    note: 'checking in',
    author: 'chidi',
    created_at: '2026-09-15T09:00:00Z',
    read_at: null,
    ...over,
  });

  const signal = (over: Partial<Signal> = {}): Signal => ({
    id: 1,
    session_id: 'sb-1',
    runtime: 'sovereign',
    kind: 'steer',
    by: 'chidi',
    text: 'please wrap up',
    ok: true,
    error: null,
    created_at: '2026-09-15T09:30:00Z',
    ...over,
  });

  it('an empty history is an empty timeline, not an error', () => {
    expect(timelineFor([], [])).toEqual([]);
  });

  it('notes and signals interleave in chronological order', () => {
    const result = timelineFor(
      [note({ created_at: '2026-09-15T09:00:00Z', note: 'first' })],
      [signal({ created_at: '2026-09-15T09:15:00Z', text: 'nudged' })],
    );
    expect(result.map(e => e.kind)).toEqual(['note', 'signal']);
  });

  it('a later note after a signal still sorts last', () => {
    const result = timelineFor(
      [note({ created_at: '2026-09-15T09:45:00Z', note: 'still going' })],
      [signal({ created_at: '2026-09-15T09:30:00Z' })],
    );
    expect(result.map(e => e.kind)).toEqual(['signal', 'note']);
  });

  it('a failed signal carries its error through, never hidden', () => {
    const result = timelineFor([], [signal({ ok: false, error: 'workflow not found' })]);
    expect(result[0]).toMatchObject({ kind: 'signal', ok: false, error: 'workflow not found' });
  });
});
