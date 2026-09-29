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
  // the epoch chain (idp#4893); absent from a backend that predates it
  epochs_snapped?: number;
  calls_under_lock?: number;
  folds_ok?: number;
  folds_failed?: number;
  last_fold_error?: string | null;
};

export function EfficiencyPanel() {
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
      <Chip>{frame.new_calls} new calls</Chip>{' '}
      <Chip>
        epochs {frame.epochs_snapped ?? 0} snapped · {frame.calls_under_lock ?? 0} calls
        under lock
      </Chip>{' '}
      <Chip>
        state folds {frame.folds_ok ?? 0} ok / {frame.folds_failed ?? 0} failed
      </Chip>
      {frame.last_fold_error && <Chip>last fold failed: {frame.last_fold_error}</Chip>}
      {error && <Chip>{error}</Chip>}
      <TokenProof />
    </div>
  );
}

// The proof (bin/estate-token-proof via GET /fleetview/efficiency/proof): the randomised holdout
// trial, counting down to its end, and the per-step dollar attribution, both labelled as what
// they are. Refreshed every 5 minutes, the backend's cache window.
type Arm = { conversations: number; calls: number; usd_per_call: number | null };
type TrialLane = {
  treat: Arm;
  control: Arm;
  pct_change_usd_per_call: number | null;
  ci95: [number, number] | null;
  verdict: string;
};
type Step = {
  what: string;
  calls: number;
  tokens: number;
  usd: number;
  snaps?: number;
  snap_cost_usd?: number;
  net_usd: number;
};
type Proof = {
  generated: string;
  calls_paired: number;
  trial: { started: string | null; ends: string | null; lanes: Record<string, TrialLane> };
  estimate: {
    input_usd_billed: number;
    net_saved_usd: number;
    steps: Record<string, Step>;
  };
};

const usd = (v: number) => `$${v.toFixed(2)}`;

function countdown(ends: string | null, now: number): string {
  if (!ends) return 'starts on the first call after this router change';
  const ms = Date.parse(ends) - now;
  if (ms <= 0) return 'complete';
  const h = Math.floor(ms / 3_600_000);
  const m = Math.floor((ms % 3_600_000) / 60_000);
  const s = Math.floor((ms % 60_000) / 1000);
  return `${Math.floor(h / 24)}d ${h % 24}h ${m}m ${s}s left`;
}

function TokenProof() {
  const discoveryApi = useApi(discoveryApiRef);
  const [proof, setProof] = useState<Proof | null>(null);
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    let cancelled = false;
    const read = async () => {
      try {
        const base = await discoveryApi.getBaseUrl('proxy');
        const res = await fetch(`${base}/fleetview/efficiency/proof`);
        if (!cancelled && res.ok) setProof((await res.json()) as Proof);
      } catch {
        // the live panel above still stands; the proof arrives on the next read
      }
    };
    void read();
    const poll = window.setInterval(read, 300_000);
    const tick = window.setInterval(() => setNow(Date.now()), 1000);
    return () => {
      cancelled = true;
      window.clearInterval(poll);
      window.clearInterval(tick);
    };
  }, [discoveryApi]);

  if (!proof) return <Summary>proof: computing from the whole ledger…</Summary>;
  const lanes = Object.entries(proof.trial.lanes);
  const steps = Object.entries(proof.estimate.steps).sort((a, b) => b[1].net_usd - a[1].net_usd);
  return (
    <div data-testid="token-proof">
      <Summary>
        Trial (randomised, 25% of conversations run with every step off):{' '}
        <strong>{countdown(proof.trial.ends, now)}</strong>
      </Summary>
      {lanes.length === 0 && <Chip>no trial calls yet</Chip>}
      {lanes.map(([lane, v]) => (
        <Chip key={lane}>
          {lane}: {v.treat.calls} vs {v.control.calls} calls ·{' '}
          {v.pct_change_usd_per_call === null
            ? v.verdict
            : `${v.pct_change_usd_per_call.toFixed(1)}% $/call [${v.ci95?.[0].toFixed(1)}, ${v.ci95?.[1].toFixed(1)}] ${v.verdict}`}
        </Chip>
      ))}
      <Summary>
        Estimate (attribution, all {proof.calls_paired} calls): {usd(proof.estimate.net_saved_usd)}{' '}
        saved of {usd(proof.estimate.input_usd_billed)} input billed
      </Summary>
      {steps.map(([key, s]) => (
        <Chip key={key}>
          {key} {s.what}: {(s.tokens / 1e6).toFixed(2)}M tok · net {usd(s.net_usd)}
          {s.snaps ? ` (after ${s.snaps} snaps costing ${usd(s.snap_cost_usd ?? 0)})` : ''}
        </Chip>
      ))}
    </div>
  );
}
