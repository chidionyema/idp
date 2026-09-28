// ui/Delivery.tsx
//
// The laptop plane's own delivery view: merged -> operating (the converger's ledger), plus the
// health of every estate launchd job. docs/tickets/2026-09-27-merged-is-operating.md.
//
// A collapsed pill by default -- this is a founder surface, not a form -- that opens into a panel
// with the same sections `delivery.py` computes: alerts, the merge -> operating beam, jobs,
// unmerged runs, and delegate progress.

import { useEffect, useState } from 'react';
import { fetchApiRef, discoveryApiRef, useApi } from '@backstage/core-plugin-api';

const POLL_MS = 10000;

type AlertLevel = 'red' | 'amber';

interface DeliveryAlert {
  readonly level: AlertLevel;
  readonly code: string;
  readonly text: string;
}

interface ConvergerState {
  readonly checked_at?: string | null;
  readonly last_error?: string | null;
  readonly behind?: boolean | null;
  readonly drift?: readonly string[] | null;
  readonly current_sha?: string | null;
}

interface ConvergeRow {
  readonly sha?: string | null;
  readonly time?: string | null;
  readonly prs?: readonly (string | number)[] | null;
  readonly drift?: readonly string[] | null;
  readonly latency_s?: number | null;
}

type JobHealth = 'running' | 'ok' | 'failing' | 'orphan' | 'not-loaded';

interface JobRow {
  readonly label: string;
  readonly pid: number | null;
  readonly last_exit: number | null;
  readonly program: string | null;
  readonly program_exists: boolean;
  readonly repo: string | null;
  readonly in_release: boolean;
  readonly health: JobHealth;
}

interface UnmergedRun {
  readonly id: string | number;
  readonly intent: string | null;
  readonly harness: string | null;
  readonly started_at: string | null;
  readonly status: string | null;
}

interface DelegateStep {
  readonly id: string | number | null;
  readonly done: boolean | null;
  readonly attempts: number | null;
  readonly last_check_rc: number | null;
}

interface DelegateRun {
  readonly slug: string;
  readonly steps: readonly DelegateStep[];
}

interface DeliveryPayload {
  readonly state: ConvergerState | null;
  readonly converges: readonly ConvergeRow[];
  readonly unmerged_runs: readonly UnmergedRun[];
  readonly delegate: readonly DelegateRun[];
  readonly jobs: readonly JobRow[];
  readonly alerts: readonly DeliveryAlert[];
  readonly operating: boolean;
  readonly checked_at: string;
}

const ALERT_COLOR: Record<AlertLevel, string> = {
  red: 'text-red-400 border-red-500/40',
  amber: 'text-amber-400 border-amber-500/40',
};

const JOB_DOT: Record<JobHealth, string> = {
  running: 'bg-emerald-400',
  ok: 'bg-emerald-400',
  failing: 'bg-red-500',
  orphan: 'bg-amber-400',
  'not-loaded': 'bg-amber-400',
};

function formatLatency(seconds: number | null | undefined): string {
  if (typeof seconds !== 'number' || !Number.isFinite(seconds)) return '—';
  const total = Math.max(0, Math.round(seconds));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}m${String(s).padStart(2, '0')}s`;
}

function formatRelative(iso: string | null | undefined): string {
  if (!iso) return '—';
  const t = Date.parse(iso);
  if (!Number.isFinite(t)) return '—';
  const deltaMs = Date.now() - t;
  const s = Math.round(deltaMs / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.round(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.round(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.round(h / 24);
  return `${d}d ago`;
}

function prChips(prs: readonly (string | number)[] | null | undefined): string[] {
  if (!prs || !prs.length) return [];
  return prs.map(pr => {
    const text = String(pr);
    return text.startsWith('#') ? text : `#${text}`;
  });
}

export default function Delivery(): JSX.Element | null {
  const fetchApi = useApi(fetchApiRef);
  const discovery = useApi(discoveryApiRef);

  const [data, setData] = useState<DeliveryPayload | null>(null);
  const [unreachable, setUnreachable] = useState(false);
  const [open, setOpen] = useState(false);
  const [showAllJobs, setShowAllJobs] = useState(false);

  useEffect(() => {
    let live = true;
    let timer: ReturnType<typeof setInterval> | null = null;

    const poll = async () => {
      try {
        const base = await discovery.getBaseUrl('proxy');
        const res = await fetchApi.fetch(`${base}/fleetview/delivery`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const body: DeliveryPayload = await res.json();
        if (!live) return;
        setData(body);
        setUnreachable(false);
      } catch {
        if (!live) return;
        setUnreachable(true);
      }
    };

    void poll();
    timer = setInterval(poll, POLL_MS);

    return () => {
      live = false;
      if (timer) clearInterval(timer);
    };
  }, [fetchApi, discovery]);

  const alerts = data?.alerts ?? [];
  const hasRed = unreachable || alerts.some(a => a.level === 'red');
  const hasAmber = alerts.some(a => a.level === 'amber');
  const dotColor = hasRed ? 'bg-red-500' : hasAmber ? 'bg-amber-400' : 'bg-emerald-400';

  const jobs = data?.jobs ?? [];
  const runningOrOk = jobs.filter(j => j.health === 'running' || j.health === 'ok');
  const notableJobs = jobs.filter(j => j.health !== 'running' && j.health !== 'ok');
  const failingJobs = jobs.filter(j => j.health === 'failing');
  const jobsCountText = `${runningOrOk.length}/${jobs.length} jobs`;

  const shaShort = unreachable
    ? 'unreachable'
    : data?.state?.current_sha
      ? data.state.current_sha.slice(0, 7)
      : '—';
  const stateWord = unreachable
    ? ''
    : data?.operating
      ? 'operating'
      : alerts.find(a => a.level === 'red')
        ? alerts.find(a => a.level === 'red')!.code
        : 'behind';
  const stateColor = unreachable
    ? 'text-red-400'
    : data?.operating
      ? 'text-emerald-400'
      : alerts.find(a => a.level === 'red')
        ? 'text-red-400'
        : 'text-amber-400';

  const healthCounts: Record<JobHealth, number> = {
    running: 0,
    ok: 0,
    failing: 0,
    orphan: 0,
    'not-loaded': 0,
  };
  jobs.forEach(j => {
    healthCounts[j.health] += 1;
  });

  return (
    <div className="absolute bottom-24 right-6 z-40 font-mono text-[11px]">
      <button
        type="button"
        onClick={() => setOpen(prev => !prev)}
        className="flex items-center gap-2 rounded-full border border-white/15 bg-black/60 backdrop-blur-md px-3 py-1.5 text-white/85 hover:border-white/30"
      >
        <span className={`inline-block h-2 w-2 rounded-full animate-pulse ${dotColor}`} />
        <span className="tracking-wide">LAPTOP ◆ {shaShort}</span>
        {stateWord ? <span className={stateColor}>{stateWord}</span> : null}
        <span className={failingJobs.length > 0 ? 'text-red-400' : 'text-white/60'}>
          {jobsCountText}
        </span>
      </button>

      {open ? (
        <div className="mt-2 max-w-[380px] max-h-[60vh] overflow-auto rounded-lg border border-white/15 bg-black/70 backdrop-blur-md p-3 space-y-3 text-white/80">
          {unreachable ? (
            <div className="text-red-400">delivery unreachable</div>
          ) : (
            <>
              {alerts.length > 0 ? (
                <div className="space-y-1">
                  {alerts.map(a => (
                    <div
                      key={a.code}
                      className={`rounded border px-2 py-1 ${ALERT_COLOR[a.level]}`}
                    >
                      {a.text}
                    </div>
                  ))}
                </div>
              ) : null}

              {data && data.converges.length > 0 ? (
                <div>
                  <div className="text-white/50 mb-1">merge → operating</div>
                  <div className="relative pl-3 border-l border-white/20 space-y-2">
                    {data.converges.map((c, idx) => (
                      <div
                        key={`${c.sha ?? 'sha'}-${idx}`}
                        className={`relative ${idx === 0 ? 'animate-pulse' : ''}`}
                      >
                        <span className="absolute -left-[13px] top-1 h-2 w-2 rounded-full bg-emerald-400" />
                        <div className="flex flex-wrap items-center gap-1">
                          {prChips(c.prs).map(pr => (
                            <span
                              key={pr}
                              className="rounded bg-white/10 px-1 py-0.5 text-[10px]"
                            >
                              {pr}
                            </span>
                          ))}
                          <span className="text-white/60">{formatLatency(c.latency_s)}</span>
                          <span className="text-white/40">{formatRelative(c.time)}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}

              {jobs.length > 0 ? (
                <div>
                  <div className="flex items-center justify-between text-white/50 mb-1">
                    <span>jobs</span>
                    <button
                      type="button"
                      onClick={() => setShowAllJobs(prev => !prev)}
                      className="text-white/40 hover:text-white/70"
                    >
                      all
                    </button>
                  </div>
                  <div className="text-white/60 mb-1">
                    {healthCounts.running} running · {healthCounts.ok} ok ·{' '}
                    {healthCounts.failing} failing · {healthCounts.orphan} orphan ·{' '}
                    {healthCounts['not-loaded']} not-loaded
                  </div>
                  <div className="space-y-1">
                    {(showAllJobs ? jobs : notableJobs).map(j => (
                      <div key={j.label} className="flex items-center gap-2">
                        <span className={`inline-block h-1.5 w-1.5 rounded-full ${JOB_DOT[j.health]}`} />
                        <span className="truncate">{j.label}</span>
                        {j.health === 'failing' ? (
                          <span className="text-red-400">exit {j.last_exit}</span>
                        ) : null}
                        {!j.in_release ? (
                          <span className="text-amber-400">outside release</span>
                        ) : null}
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}

              {data && data.unmerged_runs.length > 0 ? (
                <div>
                  <div className="text-white/50 mb-1">unmerged runs</div>
                  <div className="space-y-1">
                    {data.unmerged_runs.map(r => (
                      <div key={r.id} className="flex items-center gap-2">
                        <span className="truncate">{r.intent}</span>
                        <span className="text-white/50">{r.harness}</span>
                        <span className="text-white/40">{formatRelative(r.started_at)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}

              {data && data.delegate.length > 0 ? (
                <div>
                  <div className="text-white/50 mb-1">delegate</div>
                  <div className="space-y-1">
                    {data.delegate.map(d => (
                      <div key={d.slug} className="flex items-center gap-1.5">
                        <span className="truncate">{d.slug}</span>
                        {d.steps.map((step, idx) => (
                          <span
                            key={step.id ?? idx}
                            title={`attempts ${step.attempts}, check rc ${step.last_check_rc}`}
                            className={`inline-block h-1.5 w-1.5 rounded-full ${
                              step.done ? 'bg-emerald-400' : 'bg-red-500'
                            }`}
                          />
                        ))}
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}
            </>
          )}
        </div>
      ) : null}
    </div>
  );
}
