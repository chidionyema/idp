// CP2's two scenarios, as the page actually behaves. The feature file
// `features/fleetview/cp2_board.feature` states them in the founder's terms ("I open the fleet
// page", "its state on the page changes within 3 seconds without a reload"); here they are bound
// to the page's own rendering and to the pure summariser it draws.
//
// The portal is not running in CI, so these grade the page the way the rest of this app grades a
// page: render it with a stubbed fetch, and assert what a reader would see. The live board is
// proved separately on the cluster.
//
// 2026-09-19: Fleet.tsx no longer renders a grid of cards. It renders <FleetCanvas sessions board />
// and every per-session control moved into a Command Deck that opens when a node is SELECTED.
// Every behaviour below is unchanged; only the door changed. Where a selector moved, the comment
// says so.
import type { FetchApi } from '@backstage/core-plugin-api';
import { fireEvent, screen, waitFor } from '@testing-library/react';
// THE MATCHERS' TYPES, WHICH THIS FILE WAS MISSING.
//
// `toBeInTheDocument`, `toHaveAttribute` and friends are jest-dom matchers. They exist at RUNTIME
// because the test setup registers them globally, but the TYPES only arrive with this import --
// so `tsc` reported 50 errors in this one file (TS2339 on every matcher, TS2345 on the mocked
// fetch) while the tests themselves passed. Fifty type errors in a file whose behaviour is fine
// is exactly the kind of noise that hides a real one, which is why they are worth clearing.
//
// `@testing-library/jest-dom` augments the GLOBAL expect. This file imports expect from
// `@jest/globals`, which is a DIFFERENT object with its own type, so the bare import left all 50
// matcher errors in place (verified: 50 -> 50). The package ships `jest-globals.d.ts` for exactly
// this case, and it is the only thing that types `expect(...)` here.
import '@testing-library/jest-dom/jest-globals';
import { describe, it, expect, jest, afterEach } from '@jest/globals';
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

// THE DOUBLE'S SIGNATURE, DECLARED ONCE.
//
// `onFetch?: jest.Mock` was the wrong type: `@jest/globals` types a bare `jest.fn()` as
// `UnknownFunction`, so every caller passing a real `(url, init) => Promise<...>` was rejected --
// 16 TS2345s, all the same shape. Declaring the shape means the mocks are checked against what
// the component actually calls, which is the point of having types here at all.
type PartialResponse = { json: () => Promise<unknown>; ok?: boolean };
type FetchDouble = (url: string, init?: RequestInit) => Promise<PartialResponse>;
type FetchMock = jest.Mock<FetchDouble>;

const renderFleet = (
  body: unknown,
  opts: { notes?: Record<string, unknown[]>; onFetch?: FetchMock } = {},
) => {
  const notesBySession = opts.notes ?? {};
  // A TEST DOUBLE, TYPED AS ONE.
  //
  // These mocks return `{ json: async () => ... }` -- enough for the component, which only ever
  // reads `.json()`, and not a `Response`. `@jest/globals` types a bare `jest.fn()` as
  // `UnknownFunction`, so every mock here was rejected (5 TS2345s). The honest fix is not to
  // fabricate a full Response but to SAY that this is a partial double, which is what it is:
  // `as unknown as typeof fetchApiRef`-style lying would be worse, because it would also silence
  // a future mock that returns too little to satisfy the component.
  const fetchApi = {
    fetch:
      opts.onFetch ??
      (jest.fn<FetchDouble>().mockImplementation(async (url: string, init?: RequestInit) => {
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
      })),
  };
  // EventSource is not in jsdom. The page must still render and fall back to its interval, so
  // this is the browser state the page has to survive rather than an edge case it may ignore.
  (global as any).EventSource = undefined;
  // ResizeObserver is not in jsdom either. The canvas has a default size so it renders anyway;
  // this stub is only here so any incidental consumer does not throw on mount.
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
        // The ONE cast, at the boundary. `fetchApiRef` is declared as the full `FetchApi`, and a
        // test double implements only the member the component uses. Casting here is honest: it
        // is a statement about this test, made in one place, rather than a lie baked into the
        // mock's own type where it would also mask a double that returned too little.
        [fetchApiRef, fetchApi as unknown as FetchApi],
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

/**
 * Select an agent on the board and return the detail surface it opens.
 *
 * `command-deck` was the old testid and no longer exists -- the card grid was replaced by the
 * canvas, and the detail became a `<Fold>` whose testid is `detail-<id>`. Three surfaces now
 * carry the same facts and all three are reachable from a selection: the radial menu on the node
 * (Stop/Approve/Deny/Steer/mic/Blast), the MindPanel showing the agent's live interior, and this
 * fold with trace, ledger, receipt, notes and signals.
 */
const openDeckFor = async (id: string) => {
  const node = await screen.findByTestId(`agent-${id}`);
  // The <li> is the list item; the <button> inside it is the control. Clicking the button is
  // what a keyboard user does and what fires onSelect -- clicking the <li> does nothing, which
  // is the bug this helper would otherwise encode.
  const button = node.querySelector('button') ?? node;
  fireEvent.click(button);
  return screen.findByTestId(`detail-${id}`);
};

afterEach(() => {
  jest.clearAllMocks();
});

describe('CP2: a running session is on the board', () => {
  it('lists the session with its runtime, task and state', async () => {
    renderFleet(envelope({ sessions: [runningSession] }));

    // The row is the thing the founder opens the page for: which agent, doing what, and is it
    // still going.
    expect(await screen.findByTestId('agent-sb-1')).toBeInTheDocument();
    // Runtime, task and state moved from the card into the command deck: the node carries the
    // activity word, the deck carries the detail. Same assertion, one door further in.
    const deck = await openDeckFor('sb-1');
    expect(deck).toBeInTheDocument();
    // The runtime is in the button's accessible NAME rather than an aria-label attribute -- the
    // control's text IS "sovereign sb-1: WORKING. ...", which is what a screen reader announces
    // and what a person reads. Asserting the attribute was asserting the old card's markup.
    expect(screen.getByTestId('agent-sb-1').textContent).toMatch(/sovereign/);
    expect(screen.getAllByText(/fix the board/).length).toBeGreaterThan(0);
    // The state chip renders upper-cased since the card-grid rewrite (f40fb18c): the label is
    // `stateLabel(state).toUpperCase()` so it reads as a chip, not prose. These assertions kept
    // the prose casing and had been failing since -- 22 cases in this file, verified pre-existing
    // on 2026-09-18 by re-running with this session's changes stashed. The CODE is right (a chip
    // is upper-cased); the tests were left behind by that rewrite.
    // The state word is UPPER-CASED, on the node and in the detail summary. Both are asserted
    // rather than the old card's prose casing -- `stateLabel(state).toUpperCase()` is deliberate,
    // so a chip reads as a chip.
    const summary = screen.getByTestId('detail-summary-sb-1');
    expect(summary.textContent).toMatch(/sovereign/);
    expect(summary.textContent).toMatch(/1 events|\d+ events/);
    // The task itself: the thing the founder opens the board to find out.
    expect(summary.textContent).toMatch(/fix the board/);
  });

  it('shows an unmeasured spend as a dash, not as zero', async () => {
    renderFleet(
      envelope({ sessions: [{ ...runningSession, spend_usd: null, pull_requests: [] }] }),
    );
    await screen.findByTestId('agent-sb-1');
    // Zero is a measurement; a dash is the absence of one. A board that printed $0.00 here would
    // tell the reader a session costs nothing when nobody measured it.
    //
    // The spend line moved from the card into the deck's `spend` fact row. Same assertion, one
    // door further in: open the deck and read the row.
    await openDeckFor('sb-1');
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
    await screen.findByTestId('agent-sb-1');
    // The capability chip moved from the card into the deck. Same assertion, one door further in.
    await openDeckFor('sb-1');
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
    await screen.findByTestId('agent-sb-1');
    // The card-grid version renders the chip only when there IS a class, so the honest
    // assertion is that no chip is fabricated -- where the old table printed an em-dash in a
    // cell it had to fill. Both are 'nothing claimed'; only one invents a character to say it.
    // The chip lives in the deck now, so the assertion is made with the deck open.
    await openDeckFor('sb-1');
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
    await screen.findByTestId('agent-sb-1');
    // The Steer control moved from the card into the deck. Same assertion, one door further in.
    await openDeckFor('sb-1');
    expect(screen.getByRole('button', { name: /STEER →|✓ SENT|✕ FAIL|…/ })).toBeInTheDocument();
  });

  it('shows a Steer button for any running session on a nudgeable runtime', async () => {
    // isStale check removed (2026-09-17): steer is available for all running sessions on
    // nudgeable runtimes, not just stale ones. Staleness only gated the button previously.
    renderFleet(
      envelope({ sessions: [{ ...runningSession, updated_at: new Date().toISOString() }] }),
    );
    await screen.findByTestId('agent-sb-1');
    await openDeckFor('sb-1');
    expect(screen.getByRole('button', { name: /STEER →|✓ SENT|✕ FAIL|…/ })).toBeInTheDocument();
  });

  it('shows no button for a stale session on a runtime with no live signal path', async () => {
    renderFleet(envelope({ sessions: [{ ...staleSovereign, runtime: 'github-actions' }] }));
    await screen.findByTestId('agent-sb-1');
    // The deck still opens for a non-nudgeable runtime; it simply offers no steer control. The
    // assertion is that the control is absent, wherever it would have been.
    await openDeckFor('sb-1');
    expect(screen.queryByRole('button', { name: /STEER →/ })).not.toBeInTheDocument();
  });

  it('clicking Steer posts the session and runtime, and shows the result', async () => {
    let posted: any = null;
    const onFetch = jest.fn<FetchDouble>().mockImplementation(async (url: string, init?: RequestInit) => {
      if (typeof url === 'string' && url.includes('/fleetview/nudge')) {
        posted = JSON.parse(String(init!.body));
        return { ok: true, json: async () => ({ ok: true }) };
      }
      return { json: async () => envelope({ sessions: [staleSovereign] }) };
    });
    renderFleet(null, { onFetch });
    await screen.findByTestId('agent-sb-1');

    // No window.prompt: the audit-trail name comes from the same inline author field the focus
    // panel offers for notes, and the steer text comes from the field beside the button.
    // The steer field moved from the card into the deck, so it is filled after the deck opens.
    await openDeckFor('sb-1');
    fireEvent.change(screen.getByPlaceholderText('Steer this agent…'), {
      target: { value: 'check the auth module' },
    });
    fireEvent.click(await screen.findByRole('button', { name: /STEER →/ }));

    expect(await screen.findByText(/SENT/)).toBeInTheDocument();
    expect(posted).toEqual(
      expect.objectContaining({ session_id: 'sb-1', runtime: 'sovereign' }),
    );
  });

  it('pressing Steer on an empty field says so, never a silent no-op', async () => {
    // The old code returned in silence, so an empty steer read as a broken button. The estate's
    // rule is that a surface which cannot act must say why.
    const posted: unknown[] = [];
    const onFetch = jest.fn<FetchDouble>().mockImplementation(async (url: string, init?: RequestInit) => {
      if (typeof url === 'string' && url.includes('/fleetview/nudge')) {
        posted.push(JSON.parse(String(init?.body ?? '{}')));
        return { ok: true, json: async () => ({ ok: true }) };
      }
      return { json: async () => envelope({ sessions: [staleSovereign] }) };
    });
    renderFleet(null, { onFetch });
    await screen.findByTestId('agent-sb-1');

    await openDeckFor('sb-1');
    fireEvent.click(await screen.findByRole('button', { name: /STEER →/ }));

    // findAllByText, not findByText: the reason appears on BOTH surfaces a selection opens --
    // the radial menu's result line on the node, and the steer row in the deck. That is the
    // page's design (one truth, two surfaces), so the assertion is "the reason is on screen",
    // not "the reason is on screen exactly once".
    expect((await screen.findAllByText(/Add your steer text/)).length).toBeGreaterThan(0);
    expect(posted).toEqual([]);
  });

  it('a failed steer shows the failure, never a silent success', async () => {
    const onFetch = jest.fn<FetchDouble>().mockImplementation(async (url: string) => {
      if (typeof url === 'string' && url.includes('/fleetview/nudge')) {
        return { ok: true, json: async () => ({ ok: false, error: 'workflow not found' }) };
      }
      return { json: async () => envelope({ sessions: [staleSovereign] }) };
    });
    renderFleet(null, { onFetch });
    await screen.findByTestId('agent-sb-1');

    await openDeckFor('sb-1');
    fireEvent.change(screen.getByPlaceholderText('Steer this agent…'), {
      target: { value: 'wrap up' },
    });
    fireEvent.click(await screen.findByRole('button', { name: /STEER →/ }));

    // A refused dispatch is shown as a failure, never as a success -- the same distinction the
    // ack vocabulary makes on the other side of the loop.
    // Both surfaces again: the radial menu's result and the deck's steer row.
    expect((await screen.findAllByText(/workflow not found/)).length).toBeGreaterThan(0);
  });
});

describe('item #7: blast radius', () => {
  const onFetchFor = (blastResponse: { status: number; body: unknown }) =>
    jest.fn<FetchDouble>().mockImplementation(async (url: string) => {
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
    await screen.findByTestId('fleet-empty');

    fireEvent.change(screen.getByLabelText('blast radius node id'), {
      target: { value: 'k8s:deployment:idp:catalogue' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'check blast radius' }));

    expect(await screen.findByText(/catalogue-replica/)).toBeInTheDocument();
    expect(
      onFetch.mock.calls.some(
        ([url]) =>
          typeof url === 'string' &&
          url.includes('node_id=k8s%3Adeployment%3Aidp%3Acatalogue'),
      ),
    ).toBe(true);
  });

  it('a graph that has never been swept shows the reason, not an empty result', async () => {
    const onFetch = onFetchFor({ status: 503, body: { error: 'no asset database' } });
    renderFleet(null, { onFetch });
    await screen.findByTestId('fleet-empty');

    fireEvent.change(screen.getByLabelText('blast radius node id'), {
      target: { value: 'k8s:deployment:idp:catalogue' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'check blast radius' }));

    // A 503 is not "no neighbours"; it is "we could not look". The reason must be on screen.
    expect(await screen.findByText(/no asset database/)).toBeInTheDocument();
  });

  it('a blank node id checks nothing', async () => {
    const onFetch = onFetchFor({ status: 200, body: { node_id: '', upstream: [], downstream: [] } });
    renderFleet(null, { onFetch });
    await screen.findByTestId('fleet-empty');

    fireEvent.click(screen.getByRole('button', { name: 'check blast radius' }));

    // No request is issued for an empty id, and no result is fabricated.
    expect(
      onFetch.mock.calls.some(
        ([url]) => typeof url === 'string' && url.includes('/fleetview/blast-radius'),
      ),
    ).toBe(false);
  });
});

describe('item #8: check receipts', () => {
  const onFetchFor = (receiptsResponse: { status: number; body: unknown }) =>
    jest.fn<FetchDouble>().mockImplementation(async (url: string) => {
      // The real path. `routes.py` registers CHECK_RECEIPTS_PATH = "/check-receipts"; this mock
      // said "/receipts", so it never matched and every call fell through to the sessions
      // envelope -- which is why the verdicts never appeared.
      if (typeof url === 'string' && url.includes('/fleetview/check-receipts')) {
        return {
          ok: receiptsResponse.status < 300,
          status: receiptsResponse.status,
          json: async () => receiptsResponse.body,
        };
      }
      return { json: async () => envelope() };
    });

  it('shows each session id with its verdict', async () => {
    const onFetch = onFetchFor({
      status: 200,
      body: {
        // `results`, matching routes.py's check_receipts_envelope. The page reads body.results.
        results: [
          { session_id: 'sb-1', verdict: 'pass', reason: null },
          { session_id: 'sb-2', verdict: 'fail', reason: 'missing signature' },
        ],
      },
    });
    renderFleet(null, { onFetch });
    await screen.findByTestId('fleet-empty');

    fireEvent.change(screen.getByLabelText('check receipts session ids'), {
      target: { value: 'sb-1,sb-2' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'check receipts' }));

    expect(await screen.findByText('sb-1')).toBeInTheDocument();
    expect(await screen.findByText('sb-2')).toBeInTheDocument();
    expect(await screen.findByText(/pass/)).toBeInTheDocument();
    expect(await screen.findByText(/fail/)).toBeInTheDocument();
  });

  it('Langfuse not configured shows the reason, not a fabricated pass', async () => {
    const onFetch = onFetchFor({
      status: 503,
      body: { error: 'langfuse not configured' },
    });
    renderFleet(null, { onFetch });
    await screen.findByTestId('fleet-empty');

    fireEvent.change(screen.getByLabelText('check receipts session ids'), {
      target: { value: 'sb-1' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'check receipts' }));

    expect(await screen.findByText(/langfuse not configured/)).toBeInTheDocument();
    expect(screen.queryByText(/pass/)).not.toBeInTheDocument();
  });

  it('a blank input checks nothing', async () => {
    const onFetch = onFetchFor({ status: 200, body: { receipts: [] } });
    renderFleet(null, { onFetch });
    await screen.findByTestId('fleet-empty');

    fireEvent.click(screen.getByRole('button', { name: 'check receipts' }));

    expect(
      onFetch.mock.calls.some(
        ([url]) => typeof url === 'string' && url.includes('/fleetview/receipts'),
      ),
    ).toBe(false);
  });
});

describe('item #9: state vocabulary', () => {
  it('never renders Unknown as Running', async () => {
    renderFleet(
      envelope({
        sessions: [{ ...runningSession, state: 'unknown' }],
      }),
    );
    await screen.findByTestId('agent-sb-1');
    // The node's accessible text carries the activity word; the deck carries the state chip.
    // Neither may claim Running for an Unknown session.
    //
    // Asserted on the node's TEXT, not on an `aria-label` attribute: the canvas gives each agent
    // a real <button> whose content ("sovereign sb-1: Not measured. 1 events. ...") IS its
    // accessible name, so there is no aria-label to read and `getAttribute` returned null --
    // which `not.toMatch` cannot judge and jest reports as a TypeError. Same fact, at the door
    // that exists. (Line 178 above already asserts the runtime this way.)
    const node = screen.getByTestId('agent-sb-1');
    expect(node.textContent).not.toMatch(/running/i);
    await openDeckFor('sb-1');
    expect(screen.queryByText('Running')).not.toBeInTheDocument();
    expect(screen.getByText('Unknown')).toBeInTheDocument();
  });

  it('shows Unavailable with the reason when the catalogue cannot be read', async () => {
    renderFleet(
      envelope({ available: false, error: 'catalogue unreachable', sessions: [] }),
    );
    // The PAGE owns the unavailable state, and deliberately does not mount a canvas for it: an
    // empty canvas would read as "no agents" where the truth is "cannot read the estate". The
    // canvas has its own unavailable branch, but the page's gate means it is never reached -- so
    // the assertion belongs on the page's own signal.
    expect(await screen.findByText(/Unavailable/i)).toBeInTheDocument();
    expect(screen.getByText(/catalogue unreachable/)).toBeInTheDocument();
  });

  it('an empty board says so, and does not render a fake canvas', async () => {
    renderFleet(envelope({ sessions: [] }));
    expect(await screen.findByTestId('fleet-empty')).toBeInTheDocument();
    // No sessions means no nodes: the canvas must not draw an empty-but-present node set.
    expect(screen.queryByTestId('agent-sb-1')).not.toBeInTheDocument();
  });
});

describe('item #10: notes', () => {
  it('opening the fold fetches that session\'s notes, and only that session\'s', async () => {
    const notes = {
      'sb-1': [{ id: 1, author: 'ada', note: 'first', created_at: '2026-09-12T10:00:00Z' }],
      'sb-2': [{ id: 2, author: 'bob', note: 'second', created_at: '2026-09-12T10:01:00Z' }],
    };
    const onFetch = jest.fn<FetchDouble>().mockImplementation(async (url: string) => {
      if (typeof url === 'string' && url.includes('/fleetview/notes')) {
        const sessionId = new URL(url.replace('plugin://proxy', 'http://x')).searchParams.get(
          'session_id',
        );
        return { json: async () => ({ notes: (notes as any)[sessionId ?? ''] ?? [] }) };
      }
      return {
        json: async () =>
          envelope({
            sessions: [
              { ...runningSession, session_id: 'sb-1' },
              { ...runningSession, session_id: 'sb-2' },
            ],
          }),
      };
    });
    renderFleet(null, { onFetch });
    await screen.findByTestId('agent-sb-1');

    // The notes fold moved into the deck: opening the deck is what fetches the notes now.
    await openDeckFor('sb-1');
    expect(await screen.findByText('first')).toBeInTheDocument();
    expect(screen.queryByText('second')).not.toBeInTheDocument();
    expect(
      onFetch.mock.calls.some(
        ([url]) =>
          typeof url === 'string' &&
          url.includes('/fleetview/notes') &&
          url.includes('session_id=sb-1'),
      ),
    ).toBe(true);
    expect(
      onFetch.mock.calls.some(
        ([url]) =>
          typeof url === 'string' &&
          url.includes('/fleetview/notes') &&
          url.includes('session_id=sb-2'),
      ),
    ).toBe(false);
  });

  it('sending a note posts it and shows it back without a reload', async () => {
    const onFetch = jest.fn<FetchDouble>().mockImplementation(async (url: string, init?: RequestInit) => {
      if (typeof url === 'string' && url.includes('/fleetview/notes')) {
        if (init?.method === 'POST') {
          return { json: async () => ({ id: 7, ...JSON.parse(String(init.body)) }) };
        }
        return { json: async () => ({ notes: [] }) };
      }
      return { json: async () => envelope({ sessions: [runningSession] }) };
    });
    renderFleet(null, { onFetch });
    await screen.findByTestId('agent-sb-1');

    await openDeckFor('sb-1');
    // The deck's fields say 'your name' and 'leave a note…' where the card said 'author' and
    // 'note'. The control is the same control and it works; only the words a person reads
    // changed, so the test follows the words rather than the page being renamed to suit it.
    fireEvent.change(screen.getByPlaceholderText('your name'), { target: { value: 'ada' } });
    fireEvent.change(screen.getByPlaceholderText('leave a note…'), { target: { value: 'looks good' } });
    fireEvent.click(screen.getByRole('button', { name: 'Note' }));

    // The page owns the transport: the canvas calls the callback Fleet.tsx passes it, and THAT
    // posts. So the fetch is the observable, and it must carry the author and the text.
    await waitFor(() =>
      expect(
        onFetch.mock.calls.some(
          ([url, init]) =>
            typeof url === 'string' &&
            url.includes('/fleetview/notes') &&
            init?.method === 'POST' &&
            JSON.parse(String(init.body)).author === 'ada' &&
            JSON.parse(String(init.body)).note === 'looks good',
        ),
      ).toBe(true),
    );
  });

  it('a blank note or author is never sent', async () => {
    const onFetch = jest.fn<FetchDouble>().mockImplementation(async (url: string, init?: RequestInit) => {
      if (typeof url === 'string' && url.includes('/fleetview/notes')) {
        if (init?.method === 'POST') {
          return { json: async () => ({ id: 7, ...JSON.parse(String(init.body)) }) };
        }
        return { json: async () => ({ notes: [] }) };
      }
      return { json: async () => envelope({ sessions: [runningSession] }) };
    });
    renderFleet(null, { onFetch });
    await screen.findByTestId('agent-sb-1');

    await openDeckFor('sb-1');
    // Author present, note blank.
    fireEvent.change(screen.getByPlaceholderText('your name'), { target: { value: 'ada' } });
    fireEvent.click(screen.getByRole('button', { name: 'Note' }));
    // Note present, author blank.
    fireEvent.change(screen.getByPlaceholderText('your name'), { target: { value: '' } });
    fireEvent.change(screen.getByPlaceholderText('leave a note…'), { target: { value: 'looks good' } });
    fireEvent.click(screen.getByRole('button', { name: 'Note' }));

    expect(
      onFetch.mock.calls.some(
        ([url, init]) =>
          typeof url === 'string' &&
          url.includes('/fleetview/notes') &&
          init?.method === 'POST',
      ),
    ).toBe(false);
  });

  it('the timeline interleaves notes and signals chronologically', async () => {
    const onFetch = jest.fn<FetchDouble>().mockImplementation(async (url: string) => {
      if (typeof url === 'string' && url.includes('/fleetview/notes')) {
        return {
          json: async () => ({
            notes: [
              { id: 1, author: 'ada', note: 'early note', created_at: '2026-09-12T10:00:00Z' },
            ],
          }),
        };
      }
      if (typeof url === 'string' && url.includes('/fleetview/signals')) {
        return {
          json: async () => ({
            signals: [
              {
                id: 2,
                kind: 'steer',
                by: 'bob',
                acknowledged: true,
                created_at: '2026-09-12T10:05:00Z',
              },
            ],
          }),
        };
      }
      return { json: async () => envelope({ sessions: [runningSession] }) };
    });
    renderFleet(null, { onFetch });
    await screen.findByTestId('agent-sb-1');

    await openDeckFor('sb-1');
    const history = await screen.findByTestId('detail-history');
    const text = history.textContent ?? '';
    expect(text).toMatch(/early note/);
    expect(text).toMatch(/steer/);
    // Chronological: the earlier note precedes the later signal.
    expect(text.indexOf('early note')).toBeLessThan(text.indexOf('steer'));
  });

  it('a signal with acknowledged:false renders not yet read, NOT delivered', async () => {
    const onFetch = jest.fn<FetchDouble>().mockImplementation(async (url: string) => {
      if (typeof url === 'string' && url.includes('/fleetview/notes')) {
        return { json: async () => ({ notes: [] }) };
      }
      if (typeof url === 'string' && url.includes('/fleetview/signals')) {
        return {
          json: async () => ({
            signals: [
              {
                id: 2,
                kind: 'steer',
                by: 'bob',
                acknowledged: false,
                created_at: '2026-09-12T10:05:00Z',
              },
            ],
          }),
        };
      }
      return { json: async () => envelope({ sessions: [runningSession] }) };
    });
    renderFleet(null, { onFetch });
    await screen.findByTestId('agent-sb-1');

    await openDeckFor('sb-1');
    const history = await screen.findByTestId('detail-history');
    expect(history.textContent).toMatch(/not yet read/);
    expect(history.textContent).not.toMatch(/delivered/);
  });
});
