/**
 * claims, live: who is holding which paths right now, and how stale their heartbeat is --
 * AGENTS.md section 5's promise ("The founder sees every live claim on /fleet: who, what, which
 * paths, and heartbeat age") rendered. Before this, no fleet surface contained the word.
 *
 * A claim is the estate's collision contract: it is what stops two agents editing the same file,
 * and it is what bin/claim-gate refuses a lane for violating. The backend
 * (fleetview_backend/claims.py) reads the claim comments off the open issues.
 *
 * Three states, kept apart because the founder does something different about each: a live claim
 * (someone is working now), a stale heartbeat (an agent went quiet on work that is still open),
 * and a released claim (the issue closed, so the claim is released -- AGENTS.md section 5 rule 6;
 * that is finished work, not an abandoned one). And a read that could not reach GitHub says so,
 * because "nobody holds anything" is a claim about the estate that this panel must not make when
 * it cannot see.
 */
import { useCallback, useEffect, useRef, useState } from 'react';

export type Call = (init?: RequestInit) => Promise<Response>;

export type Claim = {
  issue: number;
  title?: string | null;
  agent: string;
  paths: string[];
  heartbeat: string;
  age_s: number | null;
  live: boolean;
  reason: string;
  url: string;
  issue_open?: boolean | null;
};

export type Claims = {
  available: boolean;
  error?: string;
  claims: Claim[];
  counts?: { live?: number; released?: number; stale?: number; issues?: number };
  source?: string;
  window_h?: number;
  truncated?: boolean;
  read_at?: string;
};

/** Seconds since the heartbeat, said the way a person reads a clock. */
export function ageLine(ageS: number | null | undefined): string {
  if (ageS === null || ageS === undefined) return 'heartbeat unreadable';
  const s = Math.max(0, ageS);
  if (s < 90) return `${Math.round(s)}s ago`;
  if (s < 5400) return `${Math.round(s / 60)} min ago`;
  if (s < 2 * 86400) return `${(s / 3600).toFixed(1)} h ago`;
  return `${Math.round(s / 86400)} d ago`;
}

export function claimTone(reason: string): string {
  switch (reason) {
    case 'live':
      return 'text-emerald-300 border-emerald-400/40';
    case 'stale heartbeat':
      return 'text-amber-200 border-amber-400/40';
    case 'unreadable heartbeat':
      return 'text-rose-300 border-rose-400/40';
    default:
      return 'text-white/60 border-white/15'; // issue closed: released work, not a problem
  }
}

/** The pill's words. It counts live claims only, so it can never overstate who is working. */
export function claimLabel(data: Claims | null, err: string | null): string {
  if (err) return 'claims · unreachable';
  if (!data) return 'claims · …';
  if (!data.available) return 'claims · unreadable';
  const live = data.counts?.live ?? 0;
  const stale = data.counts?.stale ?? 0;
  const stalePart = stale ? ` · ${stale} stale` : '';
  return `claims · ${live} live${stalePart}`;
}

export function claimToneFor(data: Claims | null, err: string | null): string {
  if (err || (data && !data.available)) return 'text-rose-300 border-rose-400/40';
  if (data?.counts?.stale) return 'text-amber-200 border-amber-400/40';
  return 'text-white/80 border-white/15';
}

function BoardBody({ data, err }: { data: Claims | null; err: string | null }) {
  if (err || (data && !data.available)) {
    return (
      <p data-testid="claims-error" className="text-rose-300">
        {err || data?.error || 'the claim board answered without claims.'}
      </p>
    );
  }
  if (!data) return <p className="text-white/60">reading the claims…</p>;
  if (data.claims.length === 0) {
    return (
      <p data-testid="claims-empty" className="text-white/60">
        no claim was posted in the last {data.window_h}h.
      </p>
    );
  }
  return (
    <ul data-testid="claims-list">
      {data.claims.map(c => (
        <li key={c.issue} className="mb-2 pb-2 border-b border-white/5 last:border-0">
          <div className="flex items-baseline gap-2">
            <span
              data-testid={`claim-reason-${c.issue}`}
              className={`px-1.5 rounded border text-[12px] font-mono ${claimTone(c.reason)}`}
            >
              {c.reason}
            </span>
            <span className="font-mono text-[12px] text-white/90">{c.agent}</span>
            <span className="font-mono text-[12px] text-white/60">
              #{c.issue} · {ageLine(c.age_s)}
            </span>
          </div>
          <div className="text-[12px] text-white/75">{c.title || '(title not read)'}</div>
          <div className="font-mono text-[12px] text-cyan-200/80 break-all">
            {c.paths.join(', ')}
          </div>
        </li>
      ))}
    </ul>
  );
}

export default function ClaimsPanel({
  call,
  pollMs = 30_000,
}: {
  call: Call;
  pollMs?: number;
}) {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<Claims | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const callRef = useRef(call);
  callRef.current = call;
  const inFlight = useRef(false);

  const refresh = useCallback(async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    try {
      const res = await callRef.current();
      setData((await res.json()) as Claims);
      setErr(null);
    } catch (e: any) {
      setErr(`Fleet cannot reach the claim board (${e?.message || e}).`);
    } finally {
      inFlight.current = false;
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(() => {
      if (typeof document !== 'undefined' && document.hidden) return;
      refresh();
    }, pollMs);
    return () => clearInterval(id);
  }, [pollMs, refresh]);

  const label = claimLabel(data, err);

  return (
    <div className="pointer-events-auto flex flex-col items-end gap-2 max-w-[92vw]">
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
        className={`px-3 py-1.5 rounded-full bg-black/70 border backdrop-blur-md text-[12px] font-mono hover:text-white ${claimToneFor(
          data,
          err,
        )}`}
      >
        {label}
      </button>
      {open ? (
        <div
          role="region"
          aria-label="claims"
          className="w-[440px] max-w-[92vw] max-h-[70vh] overflow-y-auto p-3 rounded-xl bg-black/80 border border-white/10 backdrop-blur-md text-white/85 text-[12px]"
        >
          <BoardBody data={data} err={err} />
          {data && data.available ? (
            <p data-testid="claims-footnote" className="mt-2 text-[12px] font-mono text-white/60">
              {data.source} · last {data.window_h}h
              {data.truncated
                ? ' · the window filled before it ended, so older claims were not read'
                : ''}
              {data.read_at ? ` · read ${data.read_at}` : ''}
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
