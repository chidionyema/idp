// CP2's two scenarios, as the page actually behaves. The feature file
// `features/fleetview/cp2_board.feature` states them in the founder's terms ("I open the fleet
// page", "its state on the page changes within 3 seconds without a reload"); here they are bound
// to the page's own rendering and to the pure summariser it draws.
//
// The portal is not running in CI, so these grade the page the way the rest of this app grades a
// page: render it with a stubbed fetch, and assert what a reader would see. The live board is
// proved separately on the cluster.
import { screen, waitFor } from '@testing-library/react';
import {
  renderInTestApp,
  TestApiProvider,
  mockApis,
} from '@backstage/frontend-test-utils';
import { configApiRef, fetchApiRef } from '@backstage/frontend-plugin-api';
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

const renderFleet = (body: unknown) => {
  const fetchApi = {
    fetch: jest.fn().mockResolvedValue({ json: async () => body }),
  };
  // EventSource is not in jsdom. The page must still render and fall back to its interval, so
  // this is the browser state the page has to survive rather than an edge case it may ignore.
  (global as any).EventSource = undefined;
  // renderInTestApp supplies the app's providers; rendering the page bare is what left
  // EstatePage's shell undefined and produced "Element type is invalid".
  // configApiRef as well as fetchApiRef: the shell's page chrome reads the app's own config, and
  // a provider list missing it leaves the app shell unable to construct itself -- which surfaced
  // as React's "Element type is invalid" rather than as a missing-API error. EstateHome.test.tsx
  // supplies the same pair for the same reason.
  return renderInTestApp(
    <TestApiProvider
      apis={[
        [fetchApiRef, fetchApi],
        [
          configApiRef,
          mockApis.config({ data: { app: { title: 'Mumchimp estate' } } }),
        ],
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
