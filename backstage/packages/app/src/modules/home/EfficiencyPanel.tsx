// Live token efficiency on /fleet: what the LiteLLM efficiency lane did, as calls happen.
// Source is the backend's `GET /fleetview/efficiency` (polled every 5s), which reads
// the gateway's own ledger. Nothing here is computed client-side except a rate.
import { useEffect, useState } from 'react';
import { fetchApiRef, useApi } from '@backstage/frontend-plugin-api';
import { Chip, Summary } from '../shell';

type Frame = {
  since: string;
  calls_billed: number;
  cache_hit_pct: number;
  cache_saved_input_equiv: number;
  router_bytes_saved: number;
  prefix_checked: number;
  prefix_broken: number;
  new_calls?: number;
};

export type { Frame as EfficiencyFrame };

export function useEfficiencyFrame() {
  const fetchApi = useApi(fetchApiRef);
  const [frame, setFrame] = useState<Frame | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    // Polled through fetchApi, not EventSource: EventSource bypasses fetchApi's bearer token, so the
    // Backstage proxy answers the stream 401 and the panel would never leave "unreachable".
    const poll = async () => {
      try {
        const res = await fetchApi.fetch('plugin://proxy/fleetview/efficiency?since=1h');
        if (!res.ok) throw new Error(`efficiency ${res.status}`);
        const next = (await res.json()) as Frame;
        if (!cancelled) {
          setError(null);
          setFrame(next);
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      }
      if (!cancelled) timer = setTimeout(poll, 5000);
    };
    void poll();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [fetchApi]);
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
