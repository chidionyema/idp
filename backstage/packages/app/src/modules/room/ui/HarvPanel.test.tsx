import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import HarvPanel, { ageLine, groups, type Harv } from './HarvPanel';

const reply = (body: unknown): Response =>
  ({ ok: true, status: 200, json: async () => body }) as unknown as Response;

const funnel: Harv = {
  available: true,
  run_at: 1_000_000,
  shelved: 1377,
  evidence: 2957,
  shelf: { t1: 1244, t2: 118, t3: 15 },
  stages: [
    { stage: 'crates-indexed', n: 100 },
    { stage: 'crates-inventoried', n: 97 },
    { stage: 'fns-public', n: 6253 },
    { stage: 'fns-compiled', n: 1891 },
  ],
};

describe('harv panel', () => {
  it('groups stages by prefix, each bar a share of its own group', () => {
    const g = groups(funnel.stages!);
    expect(g.map(x => [x.name, x.top])).toEqual([
      ['crates', 100],
      ['fns', 6253],
    ]);
  });

  it('says how old the last run is', () => {
    expect(ageLine(null, 5)).toBe('last run unknown');
    expect(ageLine(1000, 1030)).toBe('last run just now');
    expect(ageLine(1000, 1000 + 3 * 86400)).toBe('last run 3 d ago');
  });

  it('shows the shelf, tiers and evidence', async () => {
    render(<HarvPanel call={async () => reply(funnel)} now={() => 1_000_100} />);
    await waitFor(() =>
      expect(screen.getByText('harv · 1,377 shelved')).toBeTruthy(),
    );
    fireEvent.click(screen.getByText('harv · 1,377 shelved'));
    expect(screen.getByTestId('harv-tiers').textContent).toContain('t1 · 1,244');
    expect(screen.getByTestId('harv-age').textContent).toContain('2,957 evidence');
  });

  it('flags a funnel whose last run is old instead of calling it healthy', async () => {
    render(
      <HarvPanel call={async () => reply(funnel)} now={() => 1_000_000 + 3 * 86400} />,
    );
    await waitFor(() =>
      expect(screen.getByText('harv · 1,377 shelved · stale')).toBeTruthy(),
    );
  });

  it('an unreadable harvester says why, never an empty funnel', async () => {
    render(
      <HarvPanel
        call={async () => reply({ available: false, error: 'harv binary not found' })}
      />,
    );
    await waitFor(() => expect(screen.getByText('harv · unreadable')).toBeTruthy());
    fireEvent.click(screen.getByText('harv · unreadable'));
    expect(screen.getByTestId('harv-error').textContent).toBe('harv binary not found');
  });

  it('an unreachable backend says so', async () => {
    render(
      <HarvPanel
        call={async () => {
          throw new Error('offline');
        }}
      />,
    );
    await waitFor(() => expect(screen.getByText('harv · unreachable')).toBeTruthy());
  });
});
