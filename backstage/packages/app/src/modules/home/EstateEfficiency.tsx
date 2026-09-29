// FleetView: the router's efficiency chain, live (idp#4893). Every call through the router, on
// every lane, writes a ledger row (platform/llm/efficiency_gateway.py); `GET /fleetview/efficiency`
// (src/efficiency.py) sums the last hour and day: bytes harnesses sent vs bytes the router
// forwarded, epoch snaps and calls held under a hash lock, reasoning stripped, prompt-cache hit
// rate and prefix breaks, and the background state folds. An unreadable ledger shows its reason,
// never a zero.
import { useEffect, useState } from 'react';
import { fetchApiRef, useApi } from '@backstage/frontend-plugin-api';
import { Chip } from '../shell';

type Lane = { calls: number; bytes_in: number; bytes_out: number };
type Window = {
  calls: number;
  bytes_in: number;
  bytes_out: number;
  cut_pct: number | null;
  epochs_snapped: number;
  calls_under_lock: number;
  reasoning_bytes_stripped: number;
  prefix_broken: number;
  cache_hit_pct: number | null;
  folds_ok: number;
  folds_failed: number;
  last_fold_error: string | null;
  by_lane: Record<string, Lane>;
};
type Efficiency = {
  available: boolean;
  error?: string;
  last_event_at?: string | null;
  hour?: Window;
  day?: Window;
};

const POLL_MS = 10_000;
const mb = (b: number) => `${(b / 1e6).toFixed(1)} MB`;
const pct = (v: number | null) => (v === null ? 'n/a' : `${v}%`);

function WindowRow({ label, w }: { label: string; w: Window }) {
  return (
    <div data-testid={`efficiency-${label}`}>
      <strong>{label}</strong>{' '}
      {`${w.calls} calls, ${mb(w.bytes_in)} sent -> ${mb(w.bytes_out)} forwarded (${pct(w.cut_pct)} cut), `}
      {`cache hit ${pct(w.cache_hit_pct)}, ${w.prefix_broken} prefix breaks, `}
      {`${w.epochs_snapped} epochs snapped, ${w.calls_under_lock} calls under lock, `}
      {`${mb(w.reasoning_bytes_stripped)} reasoning stripped, folds ${w.folds_ok} ok / ${w.folds_failed} failed`}
      {w.last_fold_error ? <Chip>last fold failed: {w.last_fold_error}</Chip> : null}
      <div>
        {Object.entries(w.by_lane).map(([lane, l]) => (
          <Chip key={lane}>
            {lane}: {l.calls} calls, {mb(l.bytes_in)} {'->'} {mb(l.bytes_out)}
          </Chip>
        ))}
      </div>
    </div>
  );
}

export function EstateEfficiency() {
  const fetchApi = useApi(fetchApiRef);
  const [eff, setEff] = useState<Efficiency | undefined>();
  const [error, setError] = useState<string | undefined>();

  useEffect(() => {
    let cancelled = false;
    const read = async () => {
      try {
        const res = await fetchApi.fetch('plugin://proxy/fleetview/efficiency');
        const body = (await res.json()) as Efficiency;
        if (!cancelled) {
          setEff(body);
          setError(undefined);
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      }
    };
    void read();
    const timer = window.setInterval(read, POLL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [fetchApi]);

  if (error) return <Chip>efficiency unavailable: {error}</Chip>;
  if (!eff) return <Chip>efficiency: no answer yet</Chip>;
  if (!eff.available) return <Chip>efficiency unavailable: {eff.error}</Chip>;
  return (
    <div>
      <div>last router call {eff.last_event_at ?? 'never'}</div>
      {eff.hour ? <WindowRow label="last hour" w={eff.hour} /> : null}
      {eff.day ? <WindowRow label="last day" w={eff.day} /> : null}
    </div>
  );
}
