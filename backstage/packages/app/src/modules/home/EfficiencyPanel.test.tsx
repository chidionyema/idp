// The live token-efficiency panel: it must show what the endpoint sends, and say so when it cannot
// be reached, never a number it did not receive.
import { screen } from '@testing-library/react';
import '@testing-library/jest-dom/jest-globals';
import { describe, it, expect } from '@jest/globals';
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
