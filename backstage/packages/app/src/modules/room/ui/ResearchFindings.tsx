// Research findings: what the estate's research department actually verified, not just that its
// pod is running. The backend (packages/backend/src/researchOutput.ts) reads the newest claims
// from estate-db/research.claims; this panel polls it from the Reactor's right rail, below
// KeySync, on the same 40px pitch (96/136/176/216 -> 256px).
//
// The pill summarises; the card lists. A claim's status word is always shown next to its
// colour (DESIGN-RULES 24: colour is never the only way a state is shown). An unreachable
// department says so in its own words -- "research · unreachable" -- never as "no findings",
// which would claim the engine has produced nothing when the truth is that nobody could look.
import { useCallback, useEffect, useRef, useState } from 'react';

export type Call = (init?: RequestInit) => Promise<Response>;

export type Claim = { created_at: string; status: string; statement: string };
export type Board = { available: boolean; error?: string; count?: number; claims?: Claim[] };

export function ago(iso: string, nowMs: number): string {
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return 'at an unknown time';
  const s = Math.max(0, Math.round((nowMs - t) / 1000));
  if (s < 90) return 'just now';
  if (s < 5400) return `${Math.round(s / 60)} min ago`;
  if (s < 2 * 86400) return `${Math.round(s / 3600)} h ago`;
  return `${Math.round(s / 86400)} d ago`;
}

/** The pill: how many findings the department has on record, or why it cannot be read. */
export function summary(b: Board | null, err: string | null): string {
  if (err) return 'research · unreachable';
  if (!b) return 'research · …';
  if (!b.available) return 'research · unreadable';
  const n = b.count ?? b.claims?.length ?? 0;
  if (!n) return 'research · no findings yet';
  return `research · ${n} finding${n === 1 ? '' : 's'}`;
}

export function toneOf(status: string): string {
  const s = status.toLowerCase();
  if (s.includes('verif')) return 'border-emerald-400/30 text-emerald-200/80';
  if (s.includes('fail') || s.includes('error') || s.includes('reject')) {
    return 'border-rose-400/50 text-rose-200';
  }
  return 'border-amber-400/40 text-amber-200';
}

export default function ResearchFindings({
  call,
  pollMs = 300_000,
  now = () => Date.now(),
}: {
  call: Call;
  pollMs?: number;
  now?: () => number;
}) {
  const [open, setOpen] = useState(false);
  const [board, setBoard] = useState<Board | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const callRef = useRef(call);
  callRef.current = call;
  const inFlight = useRef(false);

  const refresh = useCallback(async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    try {
      const res = await callRef.current();
      setBoard((await res.json()) as Board);
      setErr(null);
    } catch (e: any) {
      setErr(`Fleet cannot reach the research board (${e?.message || e}).`);
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

  const claims = board?.claims || [];
  const unavailable = !!err || (board !== null && !board.available);
  const tone =
    unavailable ? 'text-rose-300 border-rose-400/40' : 'text-white/80 border-white/15';

  return (
    <div className="pointer-events-auto flex flex-col items-end gap-2 max-w-[92vw]">
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
        data-testid="research-pill"
        className={`px-3 py-1.5 rounded-full bg-black/70 border backdrop-blur-md text-[12px] font-mono hover:text-white ${tone}`}
      >
        {summary(board, err)}
      </button>
      {open ? (
        <div
          role="region"
          aria-label="research findings"
          data-testid="research-card"
          className="w-[420px] max-w-[92vw] max-h-[70vh] overflow-y-auto p-3 rounded-xl bg-black/80 border border-white/10 backdrop-blur-md text-white/85 text-[12px]"
        >
          {unavailable ? (
            <p data-testid="research-error" className="text-rose-300">
              {err || board?.error || 'the research board answered without claims.'}
            </p>
          ) : !board ? (
            <p className="text-white/60">reading the research department…</p>
          ) : claims.length === 0 ? (
            <p className="text-white/60">
              The engine has answered no questions yet. Its first hourly run puts the first
              finding here.
            </p>
          ) : (
            claims.map((c, i) => (
              <div
                key={i}
                data-testid="research-claim"
                className={`mt-2 p-2 rounded-lg border ${toneOf(c.status)}`}
              >
                <div className="text-[12px] leading-snug text-white/90 break-words">
                  {c.statement}
                </div>
                <div className="mt-1 text-[12px] uppercase tracking-wider">
                  {c.status || 'unlabelled'} · {ago(c.created_at, now())}
                </div>
              </div>
            ))
          )}
        </div>
      ) : null}
    </div>
  );
}
