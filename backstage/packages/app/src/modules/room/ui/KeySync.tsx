/**
 * Key sync: is every key the estate expects actually arriving from Bitwarden? One row per
 * Bitwarden secret name, worst first. The backend (fleetview_backend/key_sync.py) reads the
 * External Secrets bridges and their failure events -- names and states only, never a value.
 *
 * A missing key shows the exact name to create in Bitwarden, because that is the one thing the
 * founder can act on. A board that cannot be read says why instead of drawing an empty list:
 * "no rows" would claim no key is expected when the truth is that nobody could look.
 */
import { useCallback, useEffect, useRef, useState } from 'react';

export type Call = (init?: RequestInit) => Promise<Response>;

export type KeyState = 'missing' | 'stopped' | 'failing' | 'unreachable' | 'synced';
export type Row = {
  name: string;
  state: KeyState;
  namespaces: Array<{ namespace: string; bridge: string; state: KeyState; since: number | null }>;
  last_ok: number | null;
  reason: string | null;
  blip?: boolean;
};
export type Alert = { namespace: string; bridge: string; state: KeyState; since: number | null };
export type Board = {
  available: boolean;
  error?: string;
  rows?: Row[];
  counts?: Partial<Record<KeyState, number>>;
  alerts?: Alert[];
};

export const STATE_LABEL: Record<KeyState, string> = {
  missing: 'not in Bitwarden',
  stopped: 'stopped syncing',
  failing: 'not syncing',
  unreachable: 'Bitwarden unreachable',
  synced: 'synced',
};

const TONE: Record<KeyState, string> = {
  missing: 'border-rose-400/50 text-rose-200',
  stopped: 'border-rose-400/50 text-rose-200',
  failing: 'border-amber-400/40 text-amber-200',
  unreachable: 'border-amber-400/40 text-amber-200',
  synced: 'border-emerald-400/30 text-emerald-200/80',
};

export function ago(t: number | null | undefined, nowS: number): string {
  if (!t) return 'never';
  const s = Math.max(0, nowS - t);
  if (s < 90) return 'just now';
  if (s < 5400) return `${Math.round(s / 60)} min ago`;
  if (s < 2 * 86400) return `${Math.round(s / 3600)} h ago`;
  return `${Math.round(s / 86400)} d ago`;
}

/** The pill: how many keys are not arriving, or that all are. */
export function summary(b: Board | null, err: string | null): string {
  if (err) return 'keys · unreachable';
  if (!b) return 'keys · …';
  if (!b.available) return 'keys · unreadable';
  const c = b.counts || {};
  const bad = (c.missing || 0) + (c.stopped || 0) + (c.failing || 0) + (c.unreachable || 0);
  const total = bad + (c.synced || 0);
  if (!bad) return `keys · all ${total} synced`;
  return `keys · ${bad} of ${total} not syncing${b.alerts?.length ? ' · router' : ''}`;
}

export default function KeySync({
  call,
  pollMs = 30_000,
  now = () => Date.now() / 1000,
}: {
  call: Call;
  pollMs?: number;
  now?: () => number;
}) {
  const [open, setOpen] = useState(false);
  const [showSynced, setShowSynced] = useState(false);
  const [board, setBoard] = useState<Board | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);
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
      setErr(`Fleet cannot reach the key board (${e?.message || e}).`);
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

  const copy = (name: string) => {
    try {
      navigator.clipboard?.writeText(name).then(
        () => setCopied(name),
        () => setCopied(null),
      );
    } catch {
      setCopied(null);
    }
  };

  const rows = (board?.rows || []).filter(r => showSynced || r.state !== 'synced');
  const alerting = !!board?.alerts?.length;
  const bad = board?.available && rows.some(r => r.state !== 'synced');
  const tone =
    err || (board && !board.available) || alerting
      ? 'text-rose-300 border-rose-400/40'
      : bad
        ? 'text-amber-200 border-amber-400/40'
        : 'text-white/80 border-white/15';

  return (
    <div className="absolute top-48 right-6 z-40 pointer-events-auto flex flex-col items-end gap-2 max-w-[92vw]">
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
        className={`px-3 py-1.5 rounded-full bg-black/70 border backdrop-blur-md text-[11px] font-mono hover:text-white ${tone}`}
      >
        {summary(board, err)}
      </button>
      {open ? (
        <div
          role="region"
          aria-label="key sync"
          className="w-[420px] max-w-[92vw] max-h-[70vh] overflow-y-auto p-3 rounded-xl bg-black/80 border border-white/10 backdrop-blur-md text-white/85 text-[12px]"
        >
          {err || (board && !board.available) ? (
            <p data-testid="keys-error" className="text-rose-300">
              {err || board?.error || 'the key board answered without rows.'}
            </p>
          ) : !board ? (
            <p className="text-white/50">reading the bridges…</p>
          ) : (
            <>
              {alerting ? (
                <p data-testid="keys-alert" className="mb-2 text-rose-300">
                  Router keys not syncing for over 5 min:{' '}
                  {board.alerts!.map(a => a.bridge).join(', ')}
                </p>
              ) : null}
              <label className="flex items-center gap-2 text-[10px] text-white/50">
                <input
                  id="keys-show-synced"
                  type="checkbox"
                  checked={showSynced}
                  onChange={e => setShowSynced(e.target.checked)}
                />
                show synced keys
              </label>
              {rows.length === 0 ? (
                <p className="mt-2 text-emerald-200/80">Every expected key is arriving.</p>
              ) : null}
              {rows.map(r => (
                <div
                  key={r.name}
                  data-state={r.state}
                  className={`mt-2 p-2 rounded-lg border ${TONE[r.state]}`}
                >
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[11px] text-white/90 break-all flex-1 min-w-0">
                      {r.name}
                    </span>
                    {r.state === 'missing' ? (
                      <button
                        type="button"
                        onClick={() => copy(r.name)}
                        className="shrink-0 px-1.5 py-0.5 rounded border border-white/20 text-[10px] text-white/70 hover:text-white"
                      >
                        {copied === r.name ? 'copied' : 'copy name'}
                      </button>
                    ) : null}
                    <span className="shrink-0 text-[10px] uppercase tracking-wider">
                      {STATE_LABEL[r.state]}
                      {r.blip ? ' · blipped' : ''}
                    </span>
                  </div>
                  <div className="mt-1 text-[10px] text-white/55">
                    {r.namespaces.map(n => n.namespace).join(' · ')} · last synced{' '}
                    {ago(r.last_ok, now())}
                  </div>
                  {r.state === 'missing' ? (
                    <div className="mt-1 text-[10px] text-white/70">
                      Create a secret named exactly{' '}
                      <span className="font-mono text-white/90">{r.name}</span> in the estate's
                      Bitwarden project.
                    </div>
                  ) : r.reason && r.state !== 'synced' ? (
                    <div className="mt-1 text-[10px] text-white/45 break-words">{r.reason}</div>
                  ) : null}
                </div>
              ))}
            </>
          )}
        </div>
      ) : null}
    </div>
  );
}
