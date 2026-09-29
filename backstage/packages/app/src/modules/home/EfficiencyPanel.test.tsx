// The live token-efficiency panel: it must show what the stream sends, and say so when there is
// no stream, never a number it did not receive.
import { act, screen } from '@testing-library/react';
import '@testing-library/jest-dom/jest-globals';
import { describe, it, expect, afterEach } from '@jest/globals';
import { renderInTestApp, TestApiProvider, mockApis } from '@backstage/frontend-test-utils';
import { discoveryApiRef } from '@backstage/frontend-plugin-api';
import { EfficiencyPanel } from './EfficiencyPanel';

class FakeEventSource {
  static last: FakeEventSource | undefined;
  url: string;
  listeners: Record<string, (e: MessageEvent) => void> = {};
  onerror: (() => void) | null = null;
  constructor(url: string) {
    this.url = url;
    FakeEventSource.last = this;
  }
  addEventListener(name: string, fn: (e: MessageEvent) => void) {
    this.listeners[name] = fn;
  }
  close() {}
}

const render = () =>
  renderInTestApp(
    <TestApiProvider apis={[[discoveryApiRef, mockApis.discovery()]]}>
      <EfficiencyPanel />
    </TestApiProvider>,
  );

afterEach(() => {
  (global as any).EventSource = undefined;
  FakeEventSource.last = undefined;
});

describe('the live efficiency panel', () => {
  it('shows the ledger numbers the stream sends', async () => {
    (global as any).EventSource = FakeEventSource;
    await render();
    await screen.findByText(/waiting for the first ledger frame/);
    await act(async () => {
      FakeEventSource.last!.listeners.efficiency({
        data: JSON.stringify({
          since: '1h',
          calls_billed: 321,
          cache_hit_pct: 97.42,
          cache_saved_input_equiv: 1,
          router_bytes_saved: 11573,
          prefix_checked: 100,
          prefix_broken: 24,
          new_calls: 3,
        }),
      } as MessageEvent);
    });
    expect(screen.getByTestId('efficiency-panel').textContent).toMatch(/321 calls/);
    expect(screen.getByTestId('efficiency-panel').textContent).toMatch(/97\.4% /);
    expect(screen.getByText(/prefix broken 24% \(24\/100\)/)).toBeInTheDocument();
    expect(FakeEventSource.last!.url).toMatch(/\/fleetview\/efficiency\/stream\?since=1h$/);
  });

  it('says the stream is unreachable when the browser has no EventSource', async () => {
    await render();
    expect(await screen.findByText('this browser has no EventSource')).toBeInTheDocument();
  });
});
