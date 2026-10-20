// The live Greenlane panel on /fleet: it shows what the endpoint sends -- the batch's checks, each
// lane's reason, the timings -- and says so when the lane cannot be read, never an empty queue.
import { screen } from '@testing-library/react';
import '@testing-library/jest-dom/jest-globals';
import {
  renderInTestApp,
  TestApiProvider,
} from '@backstage/frontend-test-utils';
import { fetchApiRef } from '@backstage/frontend-plugin-api';
import { GreenlanePanel } from './GreenlanePanel';

const render = (fake: (url: string) => Promise<unknown>) =>
  renderInTestApp(
    <TestApiProvider
      apis={[[fetchApiRef, { fetch: fake as unknown as typeof fetch }]]}
    >
      <GreenlanePanel />
    </TestApiProvider>,
  );

const LIVE = {
  available: true,
  lanes: [
    {
      name: 'lane/face-fix',
      status: 'testing',
      reason: '',
      attempts: 1,
      head: 'a',
      age_min: 12,
    },
    {
      name: 'lane/broken',
      status: 'red',
      reason: 'ci failed: offline-gate https://github.com/x/y/actions/runs/1',
      attempts: 2,
      head: 'b',
      age_min: 30,
    },
  ],
  batch: {
    id: 7,
    tip: 'ffff',
    lanes: ['lane/face-fix'],
    age_min: 9,
    checks: [
      {
        name: 'build',
        status: 'completed',
        conclusion: 'success',
        url: 'https://x/1',
      },
      { name: 'offline-gate', status: 'in_progress', conclusion: null },
    ],
  },
  recent: [
    {
      id: 6,
      lanes: ['lane/broken'],
      outcome: 'red',
      action: 'bisect',
      reason: 'offline-gate',
      took_min: 10,
      ago_min: 25,
    },
  ],
  landed: [],
  timings: {
    queue_to_land_min: { n: 4, p50: 31, p90: 55 },
    batch_cycle_min: { n: 6, p50: 12, p90: 19 },
    outcomes: { 'green/landed': 5, 'red/bisect': 1 },
  },
  sentence: 'Testing face-fix for 9 minutes; waiting on offline-gate.',
  read_at: '2026-10-20T10:00:00Z',
};

describe('the live Greenlane panel', () => {
  it('shows the batch checks, lane reasons and timings the endpoint sends', async () => {
    const urls: string[] = [];
    await render(async url => {
      urls.push(url);
      return { status: 200, ok: true, json: async () => LIVE };
    });
    await screen.findByTestId('greenlane-panel');
    expect(urls[0]).toBe('plugin://proxy/fleetview/greenlane/live');
    const text = screen.getByTestId('greenlane-panel').textContent ?? '';
    expect(text).toMatch(/waiting on offline-gate/);
    expect(text).toMatch(/push to land p50 31m · p90 55m/);
    expect(text).toMatch(/red\/bisect 1/);
    expect(screen.getAllByTestId('greenlane-check')).toHaveLength(2);
    const lanes = screen
      .getAllByTestId('greenlane-lane')
      .map(e => e.textContent);
    expect(lanes[1]).toMatch(
      /broken · red · 30m queued · attempt 2 · ci failed: offline-gate$/,
    );
  });

  it('an unreadable lane says why instead of showing an empty queue', async () => {
    await render(async () => ({
      status: 200,
      ok: true,
      json: async () => ({
        available: false,
        error: 'the Greenlane state answered 401',
      }),
    }));
    const el = await screen.findByTestId('greenlane-unavailable');
    expect(el.textContent).toMatch(/401/);
    expect(screen.queryByTestId('greenlane-panel')).toBeNull();
  });
});
