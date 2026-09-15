// CP2's two scenarios, as the page actually behaves. The feature file
// `features/fleetview/cp2_board.feature` states them in the founder's terms ("I open the fleet
// page", "its state on the page changes within 3 seconds without a reload"); here they are bound
// to the page's own rendering and to the pure summariser it draws.
//
// The portal is not running in CI, so these grade the page the way the rest of this app grades a
// page: render it with a stubbed fetch, and assert what a reader would see. The live board is
// proved separately on the cluster.
import { fireEvent, screen, waitFor } from '@testing-library/react';
import {
  renderInTestApp,
  TestApiProvider,
  mockApis,
} from '@backstage/frontend-test-utils';
import { configApiRef, discoveryApiRef, fetchApiRef } from '@backstage/frontend-plugin-api';
import { Fleet } from './Fleet';

const envelope = (over: Record<string, unknown> = {}) => ({
  available: true,
  error: null,
  sessions: [],
  unreachable: [],
  generated_at: '2026-09-12T10:00:00Z',
  ...over,
});

const runningSession = {
  session_id: 'sb-1',
  runtime: 'sovereign',
  task: 'fix the board',
  state: 'running',
  repo: 'idp',
  step: 3,
  updated_at: '2026-09-12T10:00:00Z',
  trace_url: null,
  spend_usd: 4.25,
  pull_requests: ['https://github.com/chidionyema/idp/pull/3183'],
  ticket: null,
};

const renderFleet = (
  body: unknown,
  opts: { notes?: Record<string, unknown[]>; onFetch?: jest.Mock } = {},
) => {
  const notesBySession = opts.notes ?? {};
  const fetchApi = {
    fetch:
      opts.onFetch ??
      jest.fn().mockImplementation(async (url: string, init?: RequestInit) => {
        if (typeof url === 'string' && url.includes('/fleetview/notes')) {
          if (init?.method === 'POST') {
            return { json: async () => ({ id: 1, ...JSON.parse(String(init.body)) }) };
          }
          const sessionId = new URL(url.replace('plugin://proxy', 'http://x')).searchParams.get(
            'session_id',
          );
          return { json: async () => ({ notes: notesBySession[sessionId ?? ''] ?? [] }) };
        }
        return { json: async () => body };
      }),
  };
  // EventSource is not in jsdom. The page must still render and fall back to its interval, so
  // this is the browser state the page has to survive rather than an edge case it may ignore.
  (global as any).EventSource = undefined;
  // ResizeObserver is not in jsdom either. React Flow (the estate map) uses it to size its
  // viewport; without a stub every Fleet test fails on mount, not just the map's own tests.
  if (typeof (global as any).ResizeObserver === 'undefined') {
    (global as any).ResizeObserver = class {
      observe() {}
      unobserve() {}
      disconnect() {}
    };
  }
  // renderInTestApp supplies the app's providers; rendering the page bare is what left
  // EstatePage's shell undefined and produced "Element type is invalid".
  // configApiRef as well as fetchApiRef: the shell's page chrome reads the app's own config, and
  // a provider list missing it leaves the app shell unable to construct itself -- which surfaced
  // as React's "Element type is invalid" rather than as a missing-API error. EstateHome.test.tsx
  // supplies the same pair for the same reason.
  // discoveryApiRef too: the page resolves the EventSource URL through it (the fetch goes through
  // fetchApi's plugin:// middleware, but EventSource bypasses fetchApi). EventSource is stubbed to
  // undefined above, so this mock is never actually called -- but useApi() would throw without it.
  return renderInTestApp(
    <TestApiProvider
      apis={[
        [fetchApiRef, fetchApi],
        [
          configApiRef,
          mockApis.config({ data: { app: { title: 'Mumchimp estate' } } }),
        ],
        [discoveryApiRef, mockApis.discovery()],
      ]}
    >
      <Fleet />
    </TestApiProvider>,
  );
};

describe('CP2: a running session is on the board', () => {
  it('lists the session with its runtime, task and state', async () => {
    renderFleet(envelope({ sessions: [runningSession] }));

    // The row is the thing the founder opens the page for: which agent, doing what, and is it
    // still going.
    expect(await screen.findByText('sb-1')).toBeInTheDocument();
    expect(screen.getByText('sovereign')).toBeInTheDocument();
    expect(screen.getByText('fix the board')).toBeInTheDocument();
    expect(screen.getByText('Running')).toBeInTheDocument();
    expect(screen.getByText(/1 running/)).toBeInTheDocument();
  });

  it('shows an unmeasured spend as a dash, not as zero', async () => {
    renderFleet(
      envelope({ sessions: [{ ...runningSession, spend_usd: null, pull_requests: [] }] }),
    );
    await screen.findByText('sb-1');
    // Zero is a measurement; a dash is the absence of one. A board that printed $0.00 here would
    // tell the reader a session costs nothing when nobody measured it.
    expect(screen.getAllByText('—').length).toBeGreaterThanOrEqual(2);
    expect(screen.queryByText('$0.00')).not.toBeInTheDocument();
  });
});

describe('item #5: the capability badge', () => {
  it('shows the runtime\'s real capability class and its allowed ops as a tooltip', async () => {
    renderFleet(
      envelope({
        sessions: [
          {
            ...runningSession,
            capability_class: 'engine',
            capabilities: ['fs_read', 'fs_commit', 'git_status', 'tool_result', 'doc_commit'],
          },
        ],
      }),
    );
    await screen.findByText('sb-1');
    const badge = await screen.findByText('engine');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveAttribute('title', 'fs_read, fs_commit, git_status, tool_result, doc_commit');
  });

  it('shows a dash, never a fabricated label, for a runtime with no capability-class concept', async () => {
    renderFleet(
      envelope({
        sessions: [{ ...runningSession, capability_class: null, capabilities: null }],
      }),
    );
    await screen.findByText('sb-1');
    expect(screen.queryByText('engine')).not.toBeInTheDocument();
    expect(screen.getAllByText('—').length).toBeGreaterThanOrEqual(1);
  });
});

describe('item #6: nudge a stale session', () => {
  const staleSovereign = {
    ...runningSession,
    updated_at: '2026-09-12T09:00:00Z', // far more than 20 minutes before "now" in any test run
  };

  it('shows a Nudge button for a stale sovereign session', async () => {
    renderFleet(envelope({ sessions: [staleSovereign] }));
    await screen.findByText('sb-1');
    expect(screen.getByRole('button', { name: 'Nudge' })).toBeInTheDocument();
  });

  it('shows no button for a session that is not stale', async () => {
    // isStale compares against the real wall clock, so "not stale" needs a timestamp that is
    // recent relative to whenever this test actually runs, not a fixed date in the fixture.
    renderFleet(
      envelope({ sessions: [{ ...runningSession, updated_at: new Date().toISOString() }] }),
    );
    await screen.findByText('sb-1');
    expect(screen.queryByRole('button', { name: 'Nudge' })).not.toBeInTheDocument();
  });

  it('shows no button for a stale session on a runtime with no live signal path', async () => {
    renderFleet(envelope({ sessions: [{ ...staleSovereign, runtime: 'claude-code' }] }));
    await screen.findByText('sb-1');
    expect(screen.queryByRole('button', { name: 'Nudge' })).not.toBeInTheDocument();
  });

  it('clicking Nudge posts the session and runtime, and shows the result', async () => {
    let posted: any = null;
    const onFetch = jest.fn().mockImplementation(async (url: string, init?: RequestInit) => {
      if (typeof url === 'string' && url.includes('/fleetview/nudge')) {
        posted = JSON.parse(String(init!.body));
        return { ok: true, json: async () => ({ ok: true }) };
      }
      return { json: async () => envelope({ sessions: [staleSovereign] }) };
    });
    renderFleet(null, { onFetch });
    await screen.findByText('sb-1');

    const promptSpy = jest.spyOn(window, 'prompt').mockReturnValue('chidi');
    fireEvent.click(screen.getByRole('button', { name: 'Nudge' }));

    expect(await screen.findByText(/Nudged/)).toBeInTheDocument();
    expect(posted).toEqual({ session_id: 'sb-1', runtime: 'sovereign', by: 'chidi' });
    promptSpy.mockRestore();
  });

  it('a failed nudge shows the failure, never a silent success', async () => {
    const onFetch = jest.fn().mockImplementation(async (url: string) => {
      if (typeof url === 'string' && url.includes('/fleetview/nudge')) {
        return { ok: true, json: async () => ({ ok: false, error: 'workflow not found' }) };
      }
      return { json: async () => envelope({ sessions: [staleSovereign] }) };
    });
    renderFleet(null, { onFetch });
    await screen.findByText('sb-1');

    const promptSpy = jest.spyOn(window, 'prompt').mockReturnValue('chidi');
    fireEvent.click(screen.getByRole('button', { name: 'Nudge' }));

    expect(await screen.findByText(/Failed: workflow not found/)).toBeInTheDocument();
    promptSpy.mockRestore();
  });
});

describe('item #7: blast radius', () => {
  const onFetchFor = (blastResponse: { status: number; body: unknown }) =>
    jest.fn().mockImplementation(async (url: string) => {
      if (typeof url === 'string' && url.includes('/fleetview/blast-radius')) {
        return {
          ok: blastResponse.status < 300,
          status: blastResponse.status,
          json: async () => blastResponse.body,
        };
      }
      return { json: async () => envelope() };
    });

  it('checking a node shows its upstream and downstream', async () => {
    const onFetch = onFetchFor({
      status: 200,
      body: {
        node_id: 'k8s:deployment:idp:catalogue',
        upstream: [],
        downstream: [
          { node_id: 'k8s:deployment:idp:catalogue-replica', hops: 1, relation: 'replicates' },
        ],
      },
    });
    renderFleet(null, { onFetch });
    await screen.findByText('No sessions are running.');

    fireEvent.change(screen.getByLabelText('blast radius node id'), {
      target: { value: 'k8s:deployment:idp:catalogue' },
    });
    fireEvent.click(screen.getByText('Check'));

    expect(await screen.findByText(/catalogue-replica/)).toBeInTheDocument();
    expect(
      onFetch.mock.calls.some(
        ([url]: [string]) =>
          typeof url === 'string' &&
          url.includes('node_id=k8s%3Adeployment%3Aidp%3Acatalogue'),
      ),
    ).toBe(true);
  });

  it('a graph that has never been swept shows the reason, not an empty result', async () => {
    const onFetch = onFetchFor({ status: 503, body: { error: 'no asset database' } });
    renderFleet(null, { onFetch });
    await screen.findByText('No sessions are running.');

    fireEvent.change(screen.getByLabelText('blast radius node id'), {
      target: { value: 'k8s:deployment:idp:catalogue' },
    });
    fireEvent.click(screen.getByText('Check'));

    expect(await screen.findByText(/no asset database/)).toBeInTheDocument();
    expect(screen.queryByTestId('blast-radius-result')).not.toBeInTheDocument();
  });

  it('a blank node id checks nothing', async () => {
    const onFetch = onFetchFor({ status: 200, body: { node_id: 'x', upstream: [], downstream: [] } });
    renderFleet(null, { onFetch });
    await screen.findByText('No sessions are running.');

    fireEvent.click(screen.getByText('Check'));

    expect(
      onFetch.mock.calls.some(
        ([url]: [string]) => typeof url === 'string' && url.includes('/fleetview/blast-radius'),
      ),
    ).toBe(false);
  });
});

describe('item #9: check receipts', () => {
  const onFetchFor = (response: { status: number; body: unknown }) =>
    jest.fn().mockImplementation(async (url: string) => {
      if (typeof url === 'string' && url.includes('/fleetview/check-receipts')) {
        return {
          ok: response.status < 300,
          status: response.status,
          json: async () => response.body,
        };
      }
      return { json: async () => envelope() };
    });

  it('checking session ids shows each verdict', async () => {
    const onFetch = onFetchFor({
      status: 200,
      body: {
        results: [
          { session_id: 'sb-1', verdict: 'fail', reason: 'tagged status:done but recorded no observations' },
        ],
      },
    });
    renderFleet(null, { onFetch });
    await screen.findByText('No sessions are running.');

    fireEvent.change(screen.getByLabelText('check receipts session ids'), {
      target: { value: 'sb-1' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Check receipts' }));

    expect(await screen.findByText(/no observations/)).toBeInTheDocument();
    expect(
      onFetch.mock.calls.some(([url, init]: [string, RequestInit | undefined]) => {
        if (typeof url !== 'string' || !url.includes('/fleetview/check-receipts')) return false;
        return JSON.parse(String(init!.body)).session_ids.includes('sb-1');
      }),
    ).toBe(true);
  });

  it('Langfuse not configured shows the reason, not a fabricated pass', async () => {
    const onFetch = onFetchFor({ status: 503, body: { error: 'LANGFUSE_* is not configured' } });
    renderFleet(null, { onFetch });
    await screen.findByText('No sessions are running.');

    fireEvent.change(screen.getByLabelText('check receipts session ids'), {
      target: { value: 'sb-1' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Check receipts' }));

    expect(await screen.findByText(/not configured/)).toBeInTheDocument();
    expect(screen.queryByTestId('check-receipts-result')).not.toBeInTheDocument();
  });

  it('a blank input checks nothing', async () => {
    const onFetch = onFetchFor({ status: 200, body: { results: [] } });
    renderFleet(null, { onFetch });
    await screen.findByText('No sessions are running.');

    fireEvent.click(screen.getByRole('button', { name: 'Check receipts' }));

    expect(
      onFetch.mock.calls.some(
        ([url]: [string]) => typeof url === 'string' && url.includes('/fleetview/check-receipts'),
      ),
    ).toBe(false);
  });
});

describe('CP2: the board says which fact it is showing', () => {
  it('a source that could not be read reads as unavailable, never as an empty estate', async () => {
    renderFleet(envelope({ available: false, error: 'catalogue not readable' }));
    // An outage that renders as "no sessions" is the failure this whole distinction exists for.
    expect(await screen.findByText(/catalogue not readable/)).toBeInTheDocument();
    expect(screen.getByText('Unavailable')).toBeInTheDocument();
    expect(screen.queryByText('No sessions are running.')).not.toBeInTheDocument();
  });

  it('an estate with nothing running says so plainly', async () => {
    renderFleet(envelope());
    await waitFor(() =>
      expect(screen.getByText('No sessions are running.')).toBeInTheDocument(),
    );
  });

  it('a live board with a silent runtime names the gap', async () => {
    renderFleet(
      envelope({
        sessions: [runningSession],
        unreachable: ['sovereign: RuntimeError: connection refused'],
      }),
    );
    // The count is half the truth. The reader needs the missing runtime before they trust
    // "1 running".
    expect(await screen.findByText(/did not answer/)).toBeInTheDocument();
  });
});

describe('CP2: a session whose runtime did not say', () => {
  it('reads Unknown, never Running', async () => {
    renderFleet(envelope({ sessions: [{ ...runningSession, state: 'unknown' }] }));
    await screen.findByText('sb-1');
    // The catalogue knows which ledgers exist and nothing about liveness. A green row here would
    // be a claim the data does not support.
    expect(screen.getByText('Unknown')).toBeInTheDocument();
    expect(screen.queryByText('Running')).not.toBeInTheDocument();
  });
});

describe('leave a note for a session', () => {
  it('a row with no notes yet invites one, not a false zero', async () => {
    renderFleet(envelope({ sessions: [runningSession] }));
    await screen.findByText('sb-1');
    expect(screen.getByText('Leave a note')).toBeInTheDocument();
  });

  it('opening the fold fetches that session\'s notes, and only that session\'s', async () => {
    renderFleet(envelope({ sessions: [runningSession] }), {
      notes: { 'sb-1': [{ id: 1, author: 'chidi', note: 'check the budget' }] },
    });
    await screen.findByText('sb-1');
    fireEvent.click(screen.getByTestId('notes-fold-sb-1').querySelector('summary')!);
    expect(await screen.findByText(/check the budget/)).toBeInTheDocument();
    expect(screen.getByText('chidi', { exact: false })).toBeInTheDocument();
  });

  it('sending a note posts it and shows it back without a reload', async () => {
    let posted: any = null;
    const onFetch = jest.fn().mockImplementation(async (url: string, init?: RequestInit) => {
      if (typeof url === 'string' && url.includes('/fleetview/notes')) {
        if (init?.method === 'POST') {
          posted = JSON.parse(String(init.body));
          return { json: async () => ({ id: 1, ...posted }) };
        }
        return { json: async () => ({ notes: posted ? [{ id: 1, ...posted }] : [] }) };
      }
      return { json: async () => envelope({ sessions: [runningSession] }) };
    });
    renderFleet(null, { onFetch });
    await screen.findByText('sb-1');
    fireEvent.click(screen.getByTestId('notes-fold-sb-1').querySelector('summary')!);
    await screen.findByPlaceholderText('leave a note for this session');

    fireEvent.change(screen.getByLabelText('note author for sb-1'), {
      target: { value: 'chidi' },
    });
    fireEvent.change(screen.getByLabelText('note text for sb-1'), {
      target: { value: 'restart when the budget resets' },
    });
    fireEvent.click(screen.getByText('Send'));

    expect(await screen.findByText(/restart when the budget resets/)).toBeInTheDocument();
    expect(posted).toEqual({
      session_id: 'sb-1',
      runtime: 'sovereign',
      note: 'restart when the budget resets',
      author: 'chidi',
    });
  });

  it('a blank note or author is never sent', async () => {
    const onFetch = jest.fn().mockImplementation(async (url: string) => {
      if (typeof url === 'string' && url.includes('/fleetview/notes')) {
        return { json: async () => ({ notes: [] }) };
      }
      return { json: async () => envelope({ sessions: [runningSession] }) };
    });
    renderFleet(null, { onFetch });
    await screen.findByText('sb-1');
    fireEvent.click(screen.getByTestId('notes-fold-sb-1').querySelector('summary')!);
    await screen.findByPlaceholderText('leave a note for this session');

    fireEvent.click(screen.getByText('Send'));

    const postCalls = onFetch.mock.calls.filter(
      ([url, init]: [string, RequestInit | undefined]) =>
        url.includes('/fleetview/notes') && init?.method === 'POST',
    );
    expect(postCalls).toHaveLength(0);
  });
});
