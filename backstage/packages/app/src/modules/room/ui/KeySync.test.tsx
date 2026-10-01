import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import KeySync, { ago, summary, type Board } from './KeySync';

const reply = (body: unknown): Response =>
  ({ ok: true, status: 200, json: async () => body }) as unknown as Response;

const board: Board = {
  available: true,
  counts: { missing: 1, unreachable: 1, synced: 2 },
  alerts: [],
  rows: [
    {
      name: 'TYPESAFE_API_KEY',
      state: 'missing',
      namespaces: [
        { namespace: 'dagster', bridge: 'human-typesafe', state: 'missing', since: 1 },
        { namespace: 'mcp', bridge: 'human-typesafe', state: 'missing', since: 1 },
      ],
      last_ok: null,
      reason: 'no secret found',
    },
    {
      name: 'NVIDIA_API_KEY',
      state: 'unreachable',
      namespaces: [{ namespace: 'llm', bridge: 'human-nvidia', state: 'unreachable', since: 1 }],
      last_ok: 1_000_000 - 600,
      reason: '[503 Service Unavailable] upstream connect error',
    },
    {
      name: 'MOONSHOT_API_KEY',
      state: 'synced',
      namespaces: [{ namespace: 'llm', bridge: 'human-kimi', state: 'synced', since: 1 }],
      last_ok: 1_000_000 - 30,
      reason: null,
    },
  ],
};

describe('key sync panel', () => {
  it('summarises what is not arriving', () => {
    expect(summary(board, null)).toBe('keys · 2 of 4 not syncing');
    expect(summary({ available: true, counts: { synced: 3 } }, null)).toBe('keys · all 3 synced');
    expect(summary({ available: false, error: 'x' }, null)).toBe('keys · unreadable');
    expect(summary(null, 'boom')).toBe('keys · unreachable');
  });

  it('says when a key last synced', () => {
    expect(ago(null, 5)).toBe('never');
    expect(ago(1000, 1000 + 600)).toBe('10 min ago');
  });

  it('shows the exact name to create, and hides synced keys until asked', async () => {
    render(<KeySync call={async () => reply(board)} now={() => 1_000_000} />);
    await waitFor(() => expect(screen.getByText('keys · 2 of 4 not syncing')).toBeTruthy());
    fireEvent.click(screen.getByText('keys · 2 of 4 not syncing'));
    expect(screen.getAllByText('TYPESAFE_API_KEY').length).toBe(2); // the row and the instruction
    expect(screen.getByText('not in Bitwarden')).toBeTruthy();
    expect(screen.getByText('dagster · mcp · last synced never')).toBeTruthy();
    expect(screen.queryByText('MOONSHOT_API_KEY')).toBeNull();
    fireEvent.click(screen.getByLabelText('show synced keys'));
    expect(screen.getByText('MOONSHOT_API_KEY')).toBeTruthy();
  });

  it('flags router keys that have been down past the threshold', async () => {
    const alerting = {
      ...board,
      alerts: [{ namespace: 'llm', bridge: 'human-nvidia', state: 'unreachable', since: 1 }],
    } as Board;
    render(<KeySync call={async () => reply(alerting)} now={() => 1_000_000} />);
    await waitFor(() => expect(screen.getByText('keys · 2 of 4 not syncing · router')).toBeTruthy());
    fireEvent.click(screen.getByText('keys · 2 of 4 not syncing · router'));
    expect(screen.getByTestId('keys-alert').textContent).toContain('human-nvidia');
  });

  it('says why instead of drawing an empty board', async () => {
    render(
      <KeySync call={async () => reply({ available: false, error: 'kubectl not found on this host' })} />,
    );
    await waitFor(() => expect(screen.getByText('keys · unreadable')).toBeTruthy());
    fireEvent.click(screen.getByText('keys · unreadable'));
    expect(screen.getByTestId('keys-error').textContent).toContain('kubectl not found');
  });
});
