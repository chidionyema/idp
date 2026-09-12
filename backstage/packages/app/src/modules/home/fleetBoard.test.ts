import { order, prLabel, spendLabel, stateLabel, summarise } from './fleetBoard';
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
});
