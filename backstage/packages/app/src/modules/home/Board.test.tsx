// CP9: the board view. Proves the four sections render correctly from a stubbed session
// envelope, following the same pattern as Fleet.test.tsx.
//
// The portal is not running in CI, so these grade the page the way the rest of this app
// grades a page: render it with a stubbed fetch, and assert what a reader would see.
import { screen, waitFor } from '@testing-library/react';
import {
  renderInTestApp,
  TestApiProvider,
  mockApis,
} from '@backstage/frontend-test-utils';
import { configApiRef, discoveryApiRef, fetchApiRef } from '@backstage/frontend-plugin-api';
import { Board } from './Board';

const envelope = (over: Record<string, unknown> = {}) => ({
  available: true,
  error: null,
  sessions: [],
  unreachable: [],
  generated_at: '2026-09-17T10:00:00Z',
  ...over,
});

const runningSession = {
  session_id: 'sb-board-1',
  runtime: 'sovereign',
  task: 'build the board',
  state: 'running',
  repo: 'idp',
  step: 1,
  updated_at: '2026-09-17T10:00:00Z',
  trace_url: null,
  spend_usd: 3.50,
  pull_requests: ['https://github.com/chidionyema/idp/pull/3900'],
  ticket: null,
  capability_class: 'engine',
  capabilities: ['fs_read', 'fs_commit'],
};

const failedSession = {
  ...runningSession,
  session_id: 'sb-board-failed',
  state: 'failed',
  spend_usd: 1.00,
  updated_at: '2026-09-17T09:00:00Z',
  pull_requests: [],
};

const renderBoard = (body: unknown, onFetch?: jest.Mock) => {
  const fetchApi = {
    fetch:
      onFetch ??
      jest.fn().mockImplementation(async () => ({
        json: async () => body,
      })),
  };
  // EventSource is not in jsdom.
  (global as any).EventSource = undefined;
  // ResizeObserver stub: React Flow uses it.
  if (typeof (global as any).ResizeObserver === 'undefined') {
    (global as any).ResizeObserver = class {
      observe() {}
      unobserve() {}
      disconnect() {}
    };
  }
  return renderInTestApp(
    <TestApiProvider
      apis={[
        [fetchApiRef, fetchApi],
        [configApiRef, mockApis.config({ data: { app: { title: 'Mumchimp estate' } } })],
        [discoveryApiRef, mockApis.discovery()],
      ]}
    >
      <Board />
    </TestApiProvider>,
  );
};

describe('CP9: Board renders without crashing with a mocked session response', () => {
  it('renders the page title', async () => {
    renderBoard(envelope());
    await waitFor(() =>
      expect(screen.getByText('Board')).toBeInTheDocument(),
    );
  });

  it('shows the lead sentence', async () => {
    renderBoard(envelope());
    await screen.findByText(/fleet at a glance/i);
  });

  it('handles an unavailable source gracefully', async () => {
    renderBoard(envelope({ available: false, error: 'backend down' }));
    expect(await screen.findByText(/backend down/)).toBeInTheDocument();
  });
});

describe('CP9: Fleet now section', () => {
  it('shows the Fleet now section heading', async () => {
    renderBoard(envelope({ sessions: [runningSession] }));
    expect(await screen.findByText('Fleet now')).toBeInTheDocument();
  });

  it('shows a runtime row with running counts', async () => {
    renderBoard(envelope({ sessions: [runningSession] }));
    await screen.findByText('Fleet now');
    const rows = await screen.findAllByTestId('board-runtime-row');
    expect(rows.length).toBeGreaterThanOrEqual(1);
    expect(rows[0].textContent).toMatch(/sovereign/);
  });

  it('shows "No sessions running" when the estate is empty', async () => {
    renderBoard(envelope());
    await screen.findByText('Fleet now');
    expect(await screen.findByText(/No sessions running/)).toBeInTheDocument();
  });
});

describe('CP9: Waiting on you section', () => {
  it('shows the "Waiting on you" section heading', async () => {
    renderBoard(envelope({ sessions: [runningSession] }));
    expect(await screen.findByText('Waiting on you')).toBeInTheDocument();
  });

  it('shows "Nothing needs your attention" when no sessions need it', async () => {
    // A recently-updated session does not trigger attention.
    renderBoard(
      envelope({ sessions: [{ ...runningSession, updated_at: new Date().toISOString() }] }),
    );
    await screen.findByText('Waiting on you');
    expect(await screen.findByText(/Nothing needs your attention/)).toBeInTheDocument();
  });

  it('shows a failed session in the waiting-on-you table', async () => {
    renderBoard(envelope({ sessions: [failedSession] }));
    await screen.findByText('Waiting on you');
    const rows = await screen.findAllByTestId('board-waiting-row');
    expect(rows.some(r => r.textContent?.includes('sb-board-failed'))).toBe(true);
    expect(rows.some(r => r.textContent?.includes('Session failed'))).toBe(true);
  });
});

describe('CP9: Spend today section', () => {
  it('shows the "Spend today" section heading', async () => {
    renderBoard(envelope({ sessions: [runningSession] }));
    expect(await screen.findByText('Spend today')).toBeInTheDocument();
  });

  it('shows spend rows with amounts for sessions that have spend data', async () => {
    renderBoard(envelope({ sessions: [runningSession, failedSession] }));
    await screen.findByText('Spend today');
    const rows = await screen.findAllByTestId('board-spend-row');
    expect(rows.length).toBe(2);
    expect(rows.some(r => r.textContent?.includes('$3.50'))).toBe(true);
  });

  it('shows the total at the bottom', async () => {
    renderBoard(envelope({ sessions: [runningSession, failedSession] }));
    await screen.findByText('Spend today');
    // Total = 3.50 + 1.00 = 4.50
    expect(await screen.findByText(/Total today: \$4\.50/)).toBeInTheDocument();
  });

  it('says no spend data when no sessions have spend_usd', async () => {
    renderBoard(
      envelope({ sessions: [{ ...runningSession, spend_usd: null, pull_requests: [] }] }),
    );
    await screen.findByText('Spend today');
    expect(await screen.findByText(/LiteLLM proxy not configured/)).toBeInTheDocument();
  });
});

describe('CP9: Pull requests section', () => {
  it('shows the "Pull requests" section heading', async () => {
    renderBoard(envelope({ sessions: [runningSession] }));
    expect(await screen.findByText('Pull requests')).toBeInTheDocument();
  });

  it('lists open PRs from agent sessions', async () => {
    renderBoard(envelope({ sessions: [runningSession] }));
    await screen.findByText('Pull requests');
    const rows = await screen.findAllByTestId('board-pr-row');
    expect(rows.length).toBeGreaterThanOrEqual(1);
    expect(rows.some(r => r.textContent?.includes('sb-board-1'))).toBe(true);
  });

  it('shows "No pull requests open" when no sessions have PRs', async () => {
    renderBoard(
      envelope({ sessions: [{ ...runningSession, pull_requests: [] }] }),
    );
    await screen.findByText('Pull requests');
    expect(await screen.findByText(/No pull requests open/)).toBeInTheDocument();
  });
});
