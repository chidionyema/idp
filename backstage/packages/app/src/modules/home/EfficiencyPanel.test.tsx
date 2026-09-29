// The live token-efficiency panel: it must show what the endpoint sends, and say so when it cannot
// be reached, never a number it did not receive.
import { screen } from '@testing-library/react';
import '@testing-library/jest-dom/jest-globals';
import { describe, it, expect, jest } from '@jest/globals';
import { renderInTestApp, TestApiProvider } from '@backstage/frontend-test-utils';
import { fetchApiRef } from '@backstage/frontend-plugin-api';
import { EfficiencyPanel } from './EfficiencyPanel';

const render = (fake: (url: string) => Promise<unknown>) =>
  renderInTestApp(
    <TestApiProvider apis={[[fetchApiRef, { fetch: fake as unknown as typeof fetch }]]}>
      <EfficiencyPanel />
    </TestApiProvider>,
  );

describe('the live efficiency panel', () => {
  it('shows the ledger numbers the endpoint sends, fetched through the authenticated fetchApi', async () => {
    const urls: string[] = [];
    await render(async url => {
      urls.push(url);
      return {
        ok: true,
        json: async () => ({
          since: '1h',
          calls_billed: 321,
          cache_hit_pct: 97.42,
          cache_saved_input_equiv: 1,
          router_bytes_saved: 11573,
          prefix_checked: 100,
          prefix_broken: 24,
        }),
      };
    });
    await screen.findByText(/prefix broken 24% \(24\/100\)/);
    expect(screen.getByTestId('efficiency-panel').textContent).toMatch(/321 calls/);
    expect(screen.getByTestId('efficiency-panel').textContent).toMatch(/97\.4% /);
    expect(urls[0]).toBe('plugin://proxy/fleetview/efficiency?since=1h');
  });

  it('says so when the endpoint answers an error', async () => {
    await render(async () => ({ ok: false, status: 401, json: async () => ({}) }));
    expect(await screen.findByText('efficiency 401')).toBeInTheDocument();
  });
});

describe('TokenProof', () => {
  it('shows the trial countdown and the ranked steps from the proof endpoint', async () => {
    const proof = {
      generated: '2026-09-29T04:00:00Z',
      calls_paired: 12129,
      trial: { started: null, ends: null, lanes: {} },
      estimate: {
        input_usd_billed: 449.44,
        net_saved_usd: 12.56,
        steps: {
          m2: { what: 'collapse repeated lines', calls: 1, tokens: 1e6, usd: 0.4, net_usd: 0.4 },
          m7: { what: 'epoch compaction', calls: 1, tokens: 6e6, usd: 12, snaps: 4, snap_cost_usd: 0.9, net_usd: 11.29 },
        },
      },
    };
    const fake = jest.fn(async (url: string) => ({
      ok: true,
      status: 200,
      json: async () =>
        url.endsWith('/proof')
          ? proof
          : { since: '1h', calls_billed: 1, cache_hit_pct: 90, cache_saved_input_equiv: 1, router_bytes_saved: 1, prefix_checked: 1, prefix_broken: 0 },
    }));
    await renderInTestApp(
      <TestApiProvider apis={[[fetchApiRef, { fetch: fake as unknown as typeof fetch }]]}>
        <EfficiencyPanel />
      </TestApiProvider>,
    );
    expect(await screen.findByText(/\$12\.56/)).toBeInTheDocument();
    expect(screen.getByText(/starts on the first call/)).toBeInTheDocument();
    const chips = screen.getAllByText(/net \$/).map(e => e.textContent ?? '');
    expect(chips[0]).toMatch(/^m7/);
    expect(fake).toHaveBeenCalledWith('plugin://proxy/fleetview/efficiency/proof');
  });
});
