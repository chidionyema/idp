// fleetCanvas.test.tsx -- the canvas's own contract, rewritten against the DOM FleetCanvas.tsx
// actually renders: a ticker, a burn bar, an <svg data-testid="fleet-canvas"> of <g role="button">
// nodes, an empty state, an unavailable state, and a Command Deck dialog on selection.
//
// jsdom has no ResizeObserver and lays out nothing; the canvas has a default size so it renders
// anyway -- no size is mocked here.
import { fireEvent, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, jest, afterEach } from '@jest/globals';
import { render } from '@testing-library/react';
import FleetCanvas from './FleetCanvas';

type Session = {
  session_id: string;
  runtime: string;
  task: string;
  state: string;
  repo: string | null;
  step: number | null;
  updated_at: string;
  trace_url: string | null;
  spend_usd: number | null;
  pull_requests: string[];
  ticket: string | null;
  event_count?: number;
  capability_class?: string | null;
  capabilities?: string[] | null;
};

const session = (over: Partial<Session> = {}): Session => ({
  session_id: 'sb-1',
  runtime: 'sovereign',
  task: 'fix the board',
  state: 'running',
  repo: 'idp',
  step: 3,
  updated_at: '2026-09-12T10:00:00Z',
  trace_url: null,
  spend_usd: 4.25,
  pull_requests: [],
  ticket: null,
  event_count: 5,
  // `activity` is what the NODE draws -- the four states derived from evidence. It is not the
  // same as `state`, and a fixture that omits it is a session whose state nobody measured, which
  // the canvas correctly reports as "Not measured". The first version of this fixture omitted it
  // and the aria-label test then asserted /running/ against it: the test was conflating the two,
  // which is the exact distinction this whole surface exists to make.
  activity: 'thinking',
  ...over,
});

const board = (over: Record<string, unknown> = {}) => ({
  state: 'ready',
  error: null,
  generated_at: '2026-09-12T10:00:00Z',
  ...over,
});

const renderCanvas = (
  sessions: Session[],
  opts: {
    board?: Record<string, unknown>;
    onSubmitSteer?: jest.Mock;
    onAddNote?: jest.Mock;
    signalsBySession?: Record<string, Signal[]>;
    notesBySession?: Record<string, Note[]>;
    onRequestReceipt?: jest.Mock;
  } = {},
) =>
  render(
    <FleetCanvas
      sessions={sessions as any}
      board={board(opts.board) as any}
      onSubmitSteer={(opts.onSubmitSteer ?? jest.fn().mockResolvedValue({ ok: true })) as any}
      onAddNote={(opts.onAddNote ?? jest.fn().mockResolvedValue(undefined)) as any}
      signalsBySession={opts.signalsBySession as any}
      notesBySession={opts.notesBySession as any}
      onRequestReceipt={(opts.onRequestReceipt ?? jest.fn()) as any}
    />,
  );

afterEach(() => {
  jest.clearAllMocks();
});

describe('FleetCanvas: nodes', () => {
  it('renders one node per session', () => {
    renderCanvas([
      session({ session_id: 'sb-1' }),
      session({ session_id: 'sb-2' }),
      session({ session_id: 'sb-3' }),
    ]);
    expect(screen.getByTestId('session-sb-1')).toBeInTheDocument();
    expect(screen.getByTestId('session-sb-2')).toBeInTheDocument();
    expect(screen.getByTestId('session-sb-3')).toBeInTheDocument();
    expect(screen.queryByTestId('session-sb-4')).not.toBeInTheDocument();
  });

  it('every node aria-label contains its activity word', () => {
    // `activity`, not `state`. This test previously set `state` values and asserted the raw slug,
    // so it read "sovereign sb-1: Not measured" as a failure when the canvas was right -- the
    // session had no activity, and reporting that honestly is the point. The label carries the
    // PLAIN WORD (ACTIVITY_WORD), not the slug, because it is spoken to a person.
    renderCanvas([
      session({ session_id: 'sb-1', activity: 'thinking' }),
      session({ session_id: 'sb-2', activity: 'stuck' }),
    ]);
    const working = screen.getByTestId('session-sb-1');
    const stuck = screen.getByTestId('session-sb-2');
    expect(working.getAttribute('aria-label')).toMatch(/Working/i);
    expect(stuck.getAttribute('aria-label')).toMatch(/Stopped producing/i);
  });

  it('radius is monotonic in event_count', () => {
    renderCanvas([
      session({ session_id: 'sb-small', event_count: 1 }),
      session({ session_id: 'sb-large', event_count: 100 }),
    ]);
    const small = screen.getByTestId('session-sb-small');
    const large = screen.getByTestId('session-sb-large');
    const smallR = Number(small.querySelector('circle')?.getAttribute('r') ?? '0');
    const largeR = Number(large.querySelector('circle')?.getAttribute('r') ?? '0');
    expect(largeR).toBeGreaterThan(smallR);
  });

  it('a stuck session gets a halo', () => {
    renderCanvas([
      session({ session_id: 'sb-stuck', activity: 'stuck' }),
      session({ session_id: 'sb-run', activity: 'thinking' }),
    ]);
    const stuck = screen.getByTestId('session-sb-stuck');
    const run = screen.getByTestId('session-sb-run');
    // The halo is a distinct element the running node does not carry.
    expect(stuck.querySelector('[data-testid="halo"]')).not.toBeNull();
    expect(run.querySelector('[data-testid="halo"]')).toBeNull();
  });
});

describe('FleetCanvas: ticker', () => {
  it('ticker counts equal the data', () => {
    // Runtime is what the ticker filters. The first version of this test declared three
    // `sovereign` sessions and asserted a "1 otto" chip existed -- a fixture that could never
    // satisfy its own assertion.
    renderCanvas([
      session({ session_id: 'sb-1', runtime: 'sovereign' }),
      session({ session_id: 'sb-2', runtime: 'sovereign' }),
      session({ session_id: 'sb-3', runtime: 'otto' }),
    ]);
    expect(
      screen.getByRole('button', { name: /Filter: 2 sovereign/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /Filter: 1 otto/i }),
    ).toBeInTheDocument();
  });

  it('filter narrows the nodes', () => {
    renderCanvas([
      session({ session_id: 'sb-1', runtime: 'sovereign' }),
      session({ session_id: 'sb-2', runtime: 'otto' }),
    ]);
    fireEvent.click(screen.getByRole('button', { name: /Filter: 1 otto/i }));
    expect(screen.getByTestId('session-sb-2')).toBeInTheDocument();
    expect(screen.queryByTestId('session-sb-1')).not.toBeInTheDocument();
  });
});

describe('FleetCanvas: command deck', () => {
  it('Tab+Enter opens the deck', async () => {
    renderCanvas([session({ session_id: 'sb-1' })]);
    const node = screen.getByTestId('session-sb-1');
    node.focus();
    fireEvent.keyDown(node, { key: 'Enter' });
    expect(await screen.findByTestId('command-deck')).toBeInTheDocument();
  });

  it('Escape closes the deck', async () => {
    renderCanvas([session({ session_id: 'sb-1' })]);
    fireEvent.click(screen.getByTestId('session-sb-1'));
    expect(await screen.findByTestId('command-deck')).toBeInTheDocument();
    fireEvent.keyDown(document, { key: 'Escape' });
    await waitFor(() =>
      expect(screen.queryByTestId('command-deck')).not.toBeInTheDocument(),
    );
  });

  it('renders a dash for absent spend, never $0.00', async () => {
    renderCanvas([session({ session_id: 'sb-1', spend_usd: null })]);
    fireEvent.click(screen.getByTestId('session-sb-1'));
    await screen.findByTestId('command-deck');
    expect(screen.getAllByText('—').length).toBeGreaterThanOrEqual(1);
    expect(screen.queryByText('$0.00')).not.toBeInTheDocument();
  });

  it('an empty steer posts nothing', async () => {
    const onSubmitSteer = jest.fn();
    renderCanvas([session({ session_id: 'sb-1' })], { onSubmitSteer });
    fireEvent.click(screen.getByTestId('session-sb-1'));
    await screen.findByTestId('command-deck');
    fireEvent.click(screen.getByRole('button', { name: /STEER →/ }));
    // Nothing was posted, and the reader was told why rather than left with a dead button.
    expect(onSubmitSteer).not.toHaveBeenCalled();
    expect(screen.getByText(/Add your steer text first/i)).toBeInTheDocument();
  });

  it('acknowledged:false renders not yet read', async () => {
    renderCanvas([session({ session_id: 'sb-1' })], {
      signalsBySession: {
        'sb-1': [
          {
            id: 1,
            session_id: 'sb-1',
            runtime: 'sovereign',
            kind: 'steer',
            by: 'bob',
            text: 'wrap up',
            ok: true,
            error: null,
            created_at: '2026-09-12T10:05:00Z',
            read_at: null,
            acknowledged: false,
          } as any,
        ],
      },
    });
    fireEvent.click(screen.getByTestId('session-sb-1'));
    const history = await screen.findByTestId('deck-history');
    expect(history.textContent).toMatch(/not yet read/);
    expect(history.textContent).not.toMatch(/delivered/);
  });
});

describe('FleetCanvas: board states', () => {
  it('renders the empty state when there are no sessions', () => {
    renderCanvas([]);
    expect(screen.getByTestId('fleet-empty')).toBeInTheDocument();
    expect(screen.queryByTestId('fleet-canvas')).not.toBeInTheDocument();
  });

  it('renders the unavailable state with its reason', () => {
    renderCanvas([], { board: { state: 'unavailable', summary: 'catalogue unreachable' } });
    const unavailable = screen.getByTestId('fleet-unavailable');
    expect(unavailable).toBeInTheDocument();
    expect(unavailable.textContent).toMatch(/catalogue unreachable/);
  });
});
