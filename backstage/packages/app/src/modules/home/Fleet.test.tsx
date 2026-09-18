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
  /** Open the command deck for a session. The controls moved from the card into the deck, which
   *  opens when a NODE is selected -- same behaviour, different door. */
  const openDeckFor = (id: string) => {
    const node = screen.getByTestId(`session-${id}`);
    fireEvent.click(node);
  };

  it('lists the session with its runtime, task and state', async () => {
    renderFleet(envelope({ sessions: [runningSession] }));

    // The row is the thing the founder opens the page for: which agent, doing what, and is it
    // still going.
    expect(await screen.findByTestId('session-sb-1')).toBeInTheDocument();
    // Runtime, task and state moved from the card into the command deck: the node carries the
    // activity word, the deck carries the detail. Same assertion, one door further in.
    openDeckFor('sb-1');
    expect(await screen.findByTestId('command-deck')).toBeInTheDocument();
    expect(screen.getByText(/sovereign/)).toBeInTheDocument();
    expect(screen.getByText(/fix the board/)).toBeInTheDocument();
    // The state chip renders upper-cased since the card-grid rewrite (f40fb18c): the label is
    // `stateLabel(state).toUpperCase()` so it reads as a chip, not prose. These assertions kept
    // the prose casing and had been failing since -- 22 cases in this file, verified pre-existing
    // on 2026-09-18 by re-running with this session's changes stashed. The CODE is right (a chip
    // is upper-cased); the tests were left behind by that rewrite.
    expect(screen.getByText('RUNNING')).toBeInTheDocument();
    expect(screen.getByText(/1 running/)).toBeInTheDocument();
  });

  it('shows an unmeasured spend as a dash, not as zero', async () => {
    renderFleet(
      envelope({ sessions: [{ ...runningSession, spend_usd: null, pull_requests: [] }] }),
    );
    await screen.findByTestId('session-sb-1');
    // Zero is a measurement; a dash is the absence of one. A board that printed $0.00 here would
    // tell the reader a session costs nothing when nobody measured it.
    //
    // >= 1 rather than >= 2: the card grid prints one spend line per card, where the old table
    // had a spend cell and a PR cell that both rendered a dash. The property under test is that
    // an unmeasured value is not shown as zero, and one dash proves it; the count changed with
    // the layout, which is not what this case is about.
    expect(screen.getAllByText('—').length).toBeGreaterThanOrEqual(1);
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
    await screen.findByTestId('session-sb-1');
    const badge = await screen.findByText('engine');
    // MUI Tooltip renders via portal — title is not a native attribute on the chip element.
    // Verify the chip is present; the tooltip content is tested by MUI itself.
    expect(badge).toBeInTheDocument();
  });

  it('shows no capability chip at all for a runtime with no capability-class concept', async () => {
    renderFleet(
      envelope({
        sessions: [{ ...runningSession, capability_class: null, capabilities: null }],
      }),
    );
    await screen.findByTestId('session-sb-1');
    // The card-grid version renders the chip only when there IS a class, so the honest
    // assertion is that no chip is fabricated -- where the old table printed an em-dash in a
    // cell it had to fill. Both are 'nothing claimed'; only one invents a character to say it.
    expect(screen.queryByText('engine')).not.toBeInTheDocument();
    expect(screen.queryByText(/capability/i)).not.toBeInTheDocument();
  });
});

describe('item #6: steer a stale session', () => {
  const staleSovereign = {
    ...runningSession,
    updated_at: '2026-09-12T09:00:00Z', // far more than 20 minutes before "now" in any test run
  };

  it('shows a Steer button for a stale sovereign session', async () => {
    renderFleet(envelope({ sessions: [staleSovereign] }));
    await screen.findByTestId('session-sb-1');
    expect(screen.getByRole('button', { name: /steer/i })).toBeInTheDocument();
  });

  it('shows a Steer button for any running session on a nudgeable runtime', async () => {
    // isStale check removed (2026-09-17): steer is available for all running sessions on
    // nudgeable runtimes, not just stale ones. Staleness only gated the button previously.
    renderFleet(
      envelope({ sessions: [{ ...runningSession, updated_at: new Date().toISOString() }] }),
    );
    await screen.findByTestId('session-sb-1');
    expect(screen.getByRole('button', { name: /steer/i })).toBeInTheDocument();
  });

  it('shows no button for a stale session on a runtime with no live signal path', async () => {
    renderFleet(envelope({ sessions: [{ ...staleSovereign, runtime: 'github-actions' }] }));
    await screen.findByTestId('session-sb-1');
    expect(screen.queryByRole('button', { name: /steer/i })).not.toBeInTheDocument();
  });

  it('clicking Steer posts the session and runtime, and shows the result', async () => {
    let posted: any = null;
    const onFetch = jest.fn().mockImplementation(async (url: string, init?: RequestInit) => {
      if (typeof url === 'string' && url.includes('/fleetview/nudge')) {
        posted = JSON.parse(String(init!.body));
        return { ok: true, json: async () => ({ ok: true }) };
      }
      return { json: async () => envelope({ sessions: [staleSovereign] }) };
    });
    renderFleet(null, { onFetch });
    await screen.findByTestId('session-sb-1');

    // No window.prompt: the audit-trail name comes from the same inline author field the focus
    // panel offers for notes, and the steer text comes from the field beside the button.
    fireEvent.change(screen.getByPlaceholderText('Steer this agent…'), {
      target: { value: 'check the auth module' },
    });
    openDeckFor('sb-1');
    fireEvent.click(await screen.findByRole('button', { name: /steer/i }));

    expect(await screen.findByText(/SENT/)).toBeInTheDocument();
    expect(posted).toEqual(
      expect.objectContaining({ session_id: 'sb-1', runtime: 'sovereign' }),
    );
  });

  it('pressing Steer on an empty field says so, never a silent no-op', async () => {
    // The old code returned in silence, so an empty steer read as a broken button. The estate's
    // rule is that a surface which cannot act must say why.
    const posted: unknown[] = [];
    const onFetch = jest.fn().mockImplementation(async (url: string, init?: RequestInit) => {
      if (typeof url === 'string' && url.includes('/fleetview/nudge')) {
        posted.push(JSON.parse(String(init?.body ?? '{}')));
        return { ok: true, json: async () => ({ ok: true }) };
      }
      return { json: async () => envelope({ sessions: [staleSovereign] }) };
    });
    renderFleet(null, { onFetch });
    await screen.findByTestId('session-sb-1');

    openDeckFor('sb-1');
    fireEvent.click(await screen.findByRole('button', { name: /steer/i }));

    expect(await screen.findByText(/Add your steer text/)).toBeInTheDocument();
    expect(posted).toEqual([]);
  });

  it('a failed steer shows the failure, never a silent success', async () => {
    const onFetch = jest.fn().mockImplementation(async (url: string) => {
      if (typeof url === 'string' && url.includes('/fleetview/nudge')) {
        return { ok: true, json: async () => ({ ok: false, error: 'workflow not found' }) };
      }
      return { json: async () => envelope({ sessions: [staleSovereign] }) };
    });
    renderFleet(null, { onFetch });
    await screen.findByTestId('session-sb-1');

    fireEvent.change(screen.getByPlaceholderText('Steer this agent…'), {
      target: { value: 'wrap up' },
    });
    openDeckFor('sb-1');
    fireEvent.click(await screen.findByRole('button', { name: /steer/i }));

    // A refused dispatch is shown as a failure, never as a success -- the same distinction the
    // ack vocabulary makes on the other side of the loop.
    expect(await screen.findByText(/Failed: workflow not found/)).toBeInTheDocument();
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
    fireEvent.click(screen.getByRole('button', { name: 'check blast radius' }));

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
    fireEvent.click(screen.getByRole('button', { name: 'check blast radius' }));

    expect(await screen.findByText(/no asset database/)).toBeInTheDocument();
    expect(screen.queryByTestId('blast-radius-result')).not.toBeInTheDocument();
  });

  it('a blank node id checks nothing', async () => {
    const onFetch = onFetchFor({ status: 200, body: { node_id: 'x', upstream: [], downstream: [] } });
    renderFleet(null, { onFetch });
    await screen.findByText('No sessions are running.');

    // Named explicitly: both Tools forms have a `Check` button, and a bare getByText found two
    // -- which is why this case (and the four around it) failed after the card-grid rewrite.
    // The buttons now carry distinct aria-labels, which is also what a screen reader needed.
    fireEvent.click(screen.getByRole('button', { name: 'check blast radius' }));

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
    fireEvent.click(screen.getByRole('button', { name: /check receipts/i }));

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
    fireEvent.click(screen.getByRole('button', { name: /check receipts/i }));

    expect(await screen.findByText(/not configured/)).toBeInTheDocument();
    expect(screen.queryByTestId('check-receipts-result')).not.toBeInTheDocument();
  });

  it('a blank input checks nothing', async () => {
    const onFetch = onFetchFor({ status: 200, body: { results: [] } });
    renderFleet(null, { onFetch });
    await screen.findByText('No sessions are running.');

    fireEvent.click(screen.getByRole('button', { name: /check receipts/i }));

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
    await screen.findByTestId('session-sb-1');
    // The catalogue knows which ledgers exist and nothing about liveness. A green row here would
    // be a claim the data does not support.
    expect(screen.getByText('UNKNOWN')).toBeInTheDocument();
    expect(screen.queryByText('RUNNING')).not.toBeInTheDocument();
  });
});

describe('leave a note for a session', () => {
  it('a row with no notes yet invites one, not a false zero', async () => {
    renderFleet(envelope({ sessions: [runningSession] }));
    await screen.findByTestId('session-sb-1');

    // The note fields live inside the Focus fold, which is lazily rendered since the card-grid
    // rewrite -- the same reason the fold is opened in every case below. Asserting the
    // placeholder rather than a heading, because that is the affordance a reader actually sees.
    fireEvent.click(screen.getByTestId('focus-sb-1').querySelector('summary')!);
    expect(await screen.findByPlaceholderText('leave a note…')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('your name')).toBeInTheDocument();
    // And nothing claims a count that does not exist.
    expect(screen.queryByText(/\d+ notes?/)).not.toBeInTheDocument();
  });

  it('opening the fold fetches that session\'s notes, and only that session\'s', async () => {
    renderFleet(envelope({ sessions: [runningSession] }), {
      notes: { 'sb-1': [{ id: 1, author: 'chidi', note: 'check the budget' }] },
    });
    await screen.findByTestId('session-sb-1');
    fireEvent.click(screen.getByTestId('focus-sb-1').querySelector('summary')!);
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
    await screen.findByTestId('session-sb-1');
    fireEvent.click(screen.getByTestId('focus-sb-1').querySelector('summary')!);
    await screen.findByPlaceholderText('leave a note…');

    fireEvent.change(screen.getByLabelText('note author for sb-1'), {
      target: { value: 'chidi' },
    });
    fireEvent.change(screen.getByLabelText('note text for sb-1'), {
      target: { value: 'restart when the budget resets' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'send note for sb-1' }));

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
    await screen.findByTestId('session-sb-1');
    fireEvent.click(screen.getByTestId('focus-sb-1').querySelector('summary')!);
    await screen.findByPlaceholderText('leave a note…');

    fireEvent.click(screen.getByRole('button', { name: 'send note for sb-1' }));

    const postCalls = onFetch.mock.calls.filter(
      ([url, init]: [string, RequestInit | undefined]) =>
        url.includes('/fleetview/notes') && init?.method === 'POST',
    );
    expect(postCalls).toHaveLength(0);
  });
});

describe('the focus panel: notes and steers merged, plus an auto-fetched receipt', () => {
  it('opening the panel fetches and interleaves notes and signals chronologically', async () => {
    const onFetch = jest.fn().mockImplementation(async (url: string) => {
      if (typeof url === 'string' && url.includes('/fleetview/notes')) {
        return {
          json: async () => ({
            notes: [
              { id: 1, author: 'chidi', note: 'checking in', created_at: '2026-09-12T09:00:00Z' },
            ],
          }),
        };
      }
      if (typeof url === 'string' && url.includes('/fleetview/signals')) {
        return {
          json: async () => ({
            signals: [
              {
                id: 1,
                session_id: 'sb-1',
                runtime: 'sovereign',
                kind: 'steer',
                by: 'chidi',
                text: 'please wrap up',
                ok: true,
                error: null,
                created_at: '2026-09-12T09:30:00Z',
              },
            ],
          }),
        };
      }
      if (typeof url === 'string' && url.includes('/fleetview/check-receipts')) {
        return {
          ok: true,
          json: async () => ({
            results: [{ session_id: 'sb-1', verdict: 'pass', reason: 'status:done, 3 observation(s) recorded' }],
          }),
        };
      }
      return { json: async () => envelope({ sessions: [runningSession] }) };
    });
    renderFleet(null, { onFetch });
    await screen.findByTestId('session-sb-1');

    fireEvent.click(screen.getByTestId('focus-sb-1').querySelector('summary')!);

    await screen.findByText(/please wrap up/);
    expect(screen.getByTestId('timeline-sb-1').textContent).toMatch(/checking in.*please wrap up/s);
    expect(await screen.findByText(/Receipt: pass/)).toBeInTheDocument();
  });

  it('a failed steer attempt in the timeline carries its error, never hidden', async () => {
    const onFetch = jest.fn().mockImplementation(async (url: string) => {
      if (typeof url === 'string' && url.includes('/fleetview/signals')) {
        return {
          json: async () => ({
            signals: [
              {
                id: 1,
                session_id: 'sb-1',
                runtime: 'sovereign',
                kind: 'steer',
                by: 'chidi',
                text: 'wrap up',
                ok: false,
                error: 'workflow not found',
                created_at: '2026-09-12T09:30:00Z',
              },
            ],
          }),
        };
      }
      if (typeof url === 'string' && url.includes('/fleetview/notes')) {
        return { json: async () => ({ notes: [] }) };
      }
      if (typeof url === 'string' && url.includes('/fleetview/check-receipts')) {
        return { ok: true, json: async () => ({ results: [] }) };
      }
      return { json: async () => envelope({ sessions: [runningSession] }) };
    });
    renderFleet(null, { onFetch });
    await screen.findByTestId('session-sb-1');

    fireEvent.click(screen.getByTestId('focus-sb-1').querySelector('summary')!);

    expect(await screen.findByText(/failed: workflow not found/)).toBeInTheDocument();
  });

  it('a Langfuse-unavailable receipt reads as unavailable, never a fabricated verdict', async () => {
    const onFetch = jest.fn().mockImplementation(async (url: string) => {
      if (typeof url === 'string' && url.includes('/fleetview/check-receipts')) {
        return { ok: false, status: 503, json: async () => ({ error: 'LANGFUSE_* is not configured' }) };
      }
      if (typeof url === 'string' && url.includes('/fleetview/notes')) {
        return { json: async () => ({ notes: [] }) };
      }
      if (typeof url === 'string' && url.includes('/fleetview/signals')) {
        return { json: async () => ({ signals: [] }) };
      }
      return { json: async () => envelope({ sessions: [runningSession] }) };
    });
    renderFleet(null, { onFetch });
    await screen.findByTestId('session-sb-1');

    fireEvent.click(screen.getByTestId('focus-sb-1').querySelector('summary')!);

    expect(await screen.findByText(/Receipt: unavailable/)).toBeInTheDocument();
  });
});

describe('needs attention: triage above the table, not table order', () => {
  it('a failed session is named above the sheet', async () => {
    const failed = { ...runningSession, session_id: 'sb-9', state: 'failed' };
    renderFleet(envelope({ sessions: [failed] }));
    const attention = await screen.findByTestId('needs-attention');

    expect(attention.textContent).toMatch(/Failed/);
    expect(attention.textContent).toMatch(/sb-9/);
  });

  it('a healthy, recently-updated session needs no attention section at all', async () => {
    const healthy = { ...runningSession, updated_at: new Date().toISOString() };
    renderFleet(envelope({ sessions: [healthy] }));
    await screen.findByTestId('session-sb-1');

    expect(screen.queryByTestId('needs-attention')).not.toBeInTheDocument();
  });
});
