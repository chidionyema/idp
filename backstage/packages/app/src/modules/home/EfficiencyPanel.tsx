// Live token efficiency on /fleet: what the LiteLLM efficiency lane did, as calls happen.
// Source is the backend's `GET /fleetview/efficiency/stream` (SSE, one frame per 2s), which reads
// the gateway's own ledger. Nothing here is computed client-side except a rate.
import { useEffect, useState } from 'react';
import { discoveryApiRef, useApi } from '@backstage/frontend-plugin-api';
import { Chip, Summary } from '../shell';

type Frame = {
  since: string;
  calls_billed: number;
  cache_hit_pct: number;
  cache_saved_input_equiv: number;
  router_bytes_saved: number;
  prefix_checked: number;
  prefix_broken: number;
  new_calls: number;
};

export type { Frame as EfficiencyFrame };

export function useEfficiencyFrame() {
  const discoveryApi = useApi(discoveryApiRef);
  const [frame, setFrame] = useState<Frame | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let source: EventSource | undefined;
    let cancelled = false;
    void (async () => {
      try {
        const base = await discoveryApi.getBaseUrl('proxy');
        if (cancelled) return;
        if (typeof EventSource === 'undefined') {
          setError('this browser has no EventSource');
          return;
        }
        source = new EventSource(`${base}/fleetview/efficiency/stream?since=1h`);
        source.addEventListener('efficiency', event => {
          setError(null);
          setFrame(JSON.parse((event as MessageEvent).data) as Frame);
        });
        source.onerror = () => setError('efficiency stream unreachable');
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      }
    })();
    return () => {
      cancelled = true;
      source?.close();
    };
  }, [discoveryApi]);
  return { frame, error };
}

export function EfficiencyPanel() {
  const { frame, error } = useEfficiencyFrame();
  if (error && !frame) return <Summary>{error}</Summary>;
  if (!frame) return <Summary>waiting for the first ledger frame…</Summary>;

  const brokenPct = frame.prefix_checked
    ? Math.round((frame.prefix_broken / frame.prefix_checked) * 100)
    : 0;
  return (
    <div data-testid="efficiency-panel">
      <Summary>
        last {frame.since}: {frame.calls_billed} calls · cache hit{' '}
        {frame.cache_hit_pct.toFixed(1)}% · router cut {frame.router_bytes_saved} B
      </Summary>
      <Chip>
        prefix broken {brokenPct}% ({frame.prefix_broken}/{frame.prefix_checked})
      </Chip>{' '}
      <Chip>{frame.new_calls} new calls</Chip>
      {error && <Chip>{error}</Chip>}
    </div>
  );
}
