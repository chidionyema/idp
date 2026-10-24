// EVERY AGENT, UNDER EVALUATION, LIVE, on the Reactor (/fleet renders FleetReactorApp).
//
// Founder, 2026-10-23: "the founder surface must monitor evals across the estate in real time."
// Source is the backend's `GET /fleetview/evals/founder-agent`, which reads the harness's own
// ledger (`eval/founder-agent/reports/rounds.json`) and live feed (`reports/live.jsonl`). Nothing
// is computed here except the pass-rate percentage: the gate verdicts, the latency percentiles and
// the improvement closure are the harness's numbers, so the panel cannot disagree with the gate
// about whether the agent is converging.
//
// Two absences are rendered as themselves, never as a zero: the backend answering 503 (no ledger
// in this deployment -- it names the path it looked for) and a round with no previous round to
// compare against (a first round has no closure to report).
import { useEffect, useState } from 'react';
import { fetchApiRef, useApi } from '@backstage/frontend-plugin-api';
import { Chip, Summary } from '../shell';

type Verdict = Record<string, string>;

type Round = {
  round: number | null;
  started?: string;
  pass_rate?: number | null;
  // `verdict` is the backend's re-shaping of the row's own `g1` / `perf` statuses
  verdict?: Verdict;
  perf?: string;
  improvement?: string[];
  improvement_items?: { id: string; why?: string }[];
  green?: boolean;
  latency_p95_ms?: number | null;
  performance?: Performance;
};

type LiveEvent = {
  kind: string;
  at?: string;
  age_s?: number | null;
  session_id?: string;
  task?: string;
  ok?: boolean;
  status?: string;
  reason?: string;
  answered_ms?: number | null;
  cost_usd?: number;
  why?: string;
};

type Performance = {
  answered_ms?: Record<string, number | null>;
  cost_usd?: number;
  slowest?: { task: string; answered_ms: number }[];
};

type Snapshot = {
  latest?: Round | null;
  running?: {
    round: string;
    agent?: string;
    tasks?: number;
    runs?: number;
    turns_done?: number;
    age_s?: number | null;
  } | null;
  recent_green?: number;
  rounds_measured?: number;
  rounds?: Round[];
  live?: LiveEvent[];
  absent?: string;
};

const num = (v: unknown, fallback = 0): number =>
  typeof v === 'number' && Number.isFinite(v) ? v : fallback;

function verdictLine(v?: Verdict): string {
  if (!v) return 'no verdict recorded';
  return Object.entries(v)
    .map(([gate, status]) => `${gate} ${status}`)
    .join(' · ');
}

export function useFounderEvals(intervalMs = 5000) {
  const fetchApi = useApi(fetchApiRef);
  const [snap, setSnap] = useState<Snapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const poll = async () => {
      try {
        const res = await fetchApi.fetch('plugin://proxy/fleetview/evals/founder-agent?limit=200');
        const raw = (await res.json()) as Snapshot;
        if (!cancelled) {
          // 503 carries `absent`: the harness's ledger is not in this deployment. Show the
          // reason it gives, with the path, rather than an empty board that reads as "green".
          if (!res.ok || raw?.absent) {
            setError(raw?.absent ?? `evals ${res.status}`);
            setSnap(null);
          } else {
            setError(null);
            setSnap(raw);
          }
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      }
      if (!cancelled) timer = setTimeout(poll, intervalMs);
    };
    void poll();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [fetchApi, intervalMs]);
  return { snap, error };
}

export function FounderEvalsPanel() {
  const { snap, error } = useFounderEvals();
  if (error) return <Summary testId="founder-evals-absent">{error}</Summary>;
  if (!snap) return <Summary>waiting for the first eval frame…</Summary>;

  const latest = snap.latest;
  const perf = latest?.performance;
  const lat = perf?.answered_ms ?? {};
  const recent = snap.live ?? [];
  const lastTurns = recent.filter(e => e.kind === 'run.end').slice(-6);
  const notPublished = recent.find(e => e.kind === 'feed.not_published');

  return (
    <div data-testid="founder-evals-panel">
      {snap.running ? (
        <Summary>
          round {snap.running.round} running · {snap.running.agent} ·{' '}
          {num(snap.running.turns_done)}/{num(snap.running.tasks) * num(snap.running.runs)} turns
          done · started {snap.running.age_s ?? '?'}s ago
        </Summary>
      ) : (
        <Summary>
          {latest
            ? `round ${latest.round} · pass rate ${((latest.pass_rate ?? 0) * 100).toFixed(0)}% · ${verdictLine(latest.verdict)}`
            : 'no round has run yet'}
        </Summary>
      )}
      {latest?.green !== undefined && (
        <Chip>{latest.green ? 'green' : 'not green'}</Chip>
      )}{' '}
      {snap.recent_green !== undefined && (
        <Chip>
          {snap.recent_green}/{snap.rounds_measured ?? 5} green rounds
        </Chip>
      )}{' '}
      {perf && (
        <Chip>
          p50 {lat.p50 ?? '–'} ms · p95 {lat.p95 ?? '–'} ms · ${num(perf.cost_usd).toFixed(3)}
        </Chip>
      )}{' '}
      {latest?.improvement && latest.improvement.length > 0 && (
        <Chip>improvement owed {latest.improvement.length}</Chip>
      )}
      {(latest?.improvement_items ?? []).slice(0, 4).map(item => (
        <Chip key={item.id}>{item.id}</Chip>
      ))}
      {lastTurns.map(t => (
        <Chip key={`${t.session_id}-${t.task}-${t.at}`}>
          {t.ok ? 'ok' : 'FAIL'} {t.task} {t.status} {t.answered_ms ? `${t.answered_ms} ms` : ''}
        </Chip>
      ))}
      {notPublished && <Chip>feed not published: {notPublished.why}</Chip>}
    </div>
  );
}
