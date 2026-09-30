/**
 * harv: the capability harvester's funnel, live. Crates and functions come in at the top; each rung
 * (license, compile, zero-import sandbox, smoke, tests, witnesses) drops some; what is left is
 * shelved with signed evidence. The backend (fleetview_backend/harv.py) runs `harv funnel`.
 *
 * A harvester that cannot be read says why instead of drawing an empty funnel, and a funnel whose
 * last run is old says how old: "shelved" is a fact about the past, and the founder is asking
 * whether the harvester is running now.
 */
import { useCallback, useEffect, useRef, useState } from 'react';

export type Call = (init?: RequestInit) => Promise<Response>;

export type Stage = { stage: string; n: number };
export type Harv = {
  available: boolean;
  error?: string;
  stages?: Stage[];
  shelf?: Record<string, number>;
  shelved?: number;
  evidence?: number | null;
  run_at?: number | null;
};

export const STALE_S = 24 * 3600;

/** Stages group by their prefix (crates-, fns-, ...): a bar is a share of its own group's top. */
export function groups(stages: Stage[]): Array<{ name: string; rows: Stage[]; top: number }> {
  const by = new Map<string, Stage[]>();
  for (const s of stages) {
    const g = s.stage.split('-')[0];
    by.set(g, [...(by.get(g) || []), s]);
  }
  return [...by.entries()].map(([name, rows]) => ({
    name,
    rows,
    top: Math.max(...rows.map(r => r.n), 1),
  }));
}

export function ageLine(runAt: number | null | undefined, nowS: number): string {
  if (!runAt) return 'last run unknown';
  const s = Math.max(0, nowS - runAt);
  if (s < 90) return 'last run just now';
  if (s < 5400) return `last run ${Math.round(s / 60)} min ago`;
  if (s < 2 * 86400) return `last run ${Math.round(s / 3600)} h ago`;
  return `last run ${Math.round(s / 86400)} d ago`;
}

export default function HarvPanel({
  call,
  pollMs = 30_000,
  now = () => Date.now() / 1000,
}: {
  call: Call;
  pollMs?: number;
  now?: () => number;
}) {
  const [open, setOpen] = useState(false);
  const [harv, setHarv] = useState<Harv | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const callRef = useRef(call);
  callRef.current = call;
  const inFlight = useRef(false);

  const refresh = useCallback(async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    try {
      const res = await callRef.current();
      const body = (await res.json()) as Harv;
      setHarv(body);
      setErr(null);
    } catch (e: any) {
      setErr(`Fleet cannot reach harv (${e?.message || e}).`);
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

  const readable = !!harv && harv.available && !err;
  const stale =
    readable && !!harv!.run_at && now() - harv!.run_at! > STALE_S;
  const label = err
    ? 'harv · unreachable'
    : !harv
      ? 'harv · …'
      : !harv.available
        ? 'harv · unreadable'
        : `harv · ${(harv.shelved ?? 0).toLocaleString()} shelved${stale ? ' · stale' : ''}`;
  const tone =
    err || (harv && !harv.available)
      ? 'text-rose-300 border-rose-400/40'
      : stale
        ? 'text-amber-200 border-amber-400/40'
        : 'text-white/80 border-white/15';

  return (
    <div className="absolute top-[8.5rem] right-6 z-40 pointer-events-auto flex flex-col items-end gap-2 max-w-[92vw]">
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
        className={`px-3 py-1.5 rounded-full bg-black/70 border backdrop-blur-md text-[11px] font-mono hover:text-white ${tone}`}
      >
        {label}
      </button>
      {open ? (
        <div
          role="region"
          aria-label="harv"
          className="w-[380px] max-w-[92vw] max-h-[70vh] overflow-y-auto p-3 rounded-xl bg-black/80 border border-white/10 backdrop-blur-md text-white/85 text-[12px]"
        >
          {err || (harv && !harv.available) ? (
            <p data-testid="harv-error" className="text-rose-300">
              {err || harv?.error || 'harv answered without a funnel.'}
            </p>
          ) : !harv ? (
            <p className="text-white/50">reading the funnel…</p>
          ) : (
            <>
              <p
                data-testid="harv-age"
                className={stale ? 'text-amber-200' : 'text-white/55'}
              >
                {ageLine(harv.run_at, now())}
                {harv.evidence != null
                  ? ` · ${harv.evidence.toLocaleString()} evidence entries`
                  : ''}
              </p>
              <div className="flex gap-1 mt-2" data-testid="harv-tiers">
                {Object.entries(harv.shelf || {}).map(([t, n]) => (
                  <span
                    key={t}
                    className="px-1.5 py-0.5 rounded border border-emerald-400/40 text-emerald-200 text-[10px] font-mono"
                  >
                    {t} · {n.toLocaleString()}
                  </span>
                ))}
              </div>
              {groups(harv.stages || []).map(g => (
                <div key={g.name} className="mt-3" data-group={g.name}>
                  <div className="text-[9px] uppercase tracking-wider text-white/40">
                    {g.name}
                  </div>
                  {g.rows.map(r => (
                    <div key={r.stage} className="flex items-center gap-2 mt-1">
                      <span className="w-40 shrink-0 font-mono text-[10px] text-white/70 truncate">
                        {r.stage}
                      </span>
                      <span className="flex-1 h-1.5 rounded bg-white/5">
                        <span
                          className="block h-full rounded bg-cyan-400/70"
                          style={{ width: `${Math.max(2, (r.n / g.top) * 100)}%` }}
                        />
                      </span>
                      <span className="w-12 text-right font-mono text-[10px]">
                        {r.n.toLocaleString()}
                      </span>
                    </div>
                  ))}
                </div>
              ))}
            </>
          )}
        </div>
      ) : null}
    </div>
  );
}
