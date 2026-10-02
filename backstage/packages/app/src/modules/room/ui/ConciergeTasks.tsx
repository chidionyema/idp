/**
 * Concierge tasks: say or type a browser task, then watch the concierge do it in the founder's
 * Chrome, step by step, as it happens.
 *
 * The backend (fleetview_backend/concierge_tasks.py) starts the committed `concierge-task` intent
 * and reads back the events file it appends to while the browser runs, so a task started by voice
 * ("concierge, ...") shows here the same as one typed. The concierge never types a card and stops
 * at any pay step; the hold is reported here as `held`.
 *   - a refusal shows the backend's own reason, and the typed goal is KEPT;
 *   - a double tap is one request;
 *   - a board off the laptop says why instead of showing an empty list.
 * It polls while mounted: fast while a task is running or the panel is open, slowly otherwise,
 * never two polls at once, not while the tab is hidden, and not at all once unmounted.
 */
import { useCallback, useEffect, useRef, useState } from 'react';

export type Call = (init?: RequestInit) => Promise<Response>;

export type TaskEvent = { step: number; kind: string; text: string };

export type Task = {
  task_id: string;
  goal: string;
  started_at: number;
  updated_at: number;
  state: 'running' | 'done' | 'held' | 'failed';
  outcome: string;
  summary: string;
  last: string;
  last_kind: string;
  url: string;
  steps: number;
  found: string[];
  receipt: string | null;
  events: TaskEvent[];
};

export const MAX_GOAL_CHARS = 1000; // concierge_tasks.MAX_GOAL_CHARS

type Notice = { ok: boolean; text: string } | null;

const STATE: Record<Task['state'], string> = {
  running: 'bg-cyan-500/25 text-cyan-100 border-cyan-400/50 animate-pulse',
  done: 'bg-emerald-500/25 text-emerald-200 border-emerald-400/50',
  held: 'bg-amber-500/25 text-amber-100 border-amber-400/50',
  failed: 'bg-rose-500/25 text-rose-200 border-rose-400/50',
};

const KIND: Record<string, string> = {
  found: 'text-emerald-300',
  hold: 'text-amber-300',
  released: 'text-amber-200',
  needs_human: 'text-rose-300',
  failed: 'text-rose-300',
  done: 'text-emerald-300',
  retry: 'text-white/40',
  act: 'text-cyan-200/80',
  plan: 'text-white/70',
};

async function bodyOf(res: Response): Promise<any> {
  try {
    return await res.json();
  } catch {
    return null;
  }
}

/** What the founder reads after pressing Send. */
export function sentLine(task: { task_id: string }): string {
  return `The concierge is on it (task ${task.task_id}). It stops before paying.`;
}

/** The one line a closed pill shows for a task. */
export function headline(t: Task): string {
  if (t.state === 'running') return t.last || 'Opening the browser…';
  return t.summary || t.last || t.outcome;
}

export default function ConciergeTasks({
  call,
  pollMs = 3_000,
  idlePollMs = 30_000,
}: {
  call: Call;
  pollMs?: number;
  idlePollMs?: number;
}) {
  const [open, setOpen] = useState(false);
  const [goal, setGoal] = useState('');
  const [url, setUrl] = useState('');
  const [sending, setSending] = useState(false);
  const [notice, setNotice] = useState<Notice>(null);
  const [tasks, setTasks] = useState<Task[] | null>(null);
  const [boardError, setBoardError] = useState<string | null>(null);

  const callRef = useRef(call);
  callRef.current = call;
  const inFlight = useRef(false);

  const refresh = useCallback(async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    try {
      const res = await callRef.current();
      const body = await bodyOf(res);
      if (body && Array.isArray(body.tasks) && body.available !== false) {
        setTasks(body.tasks);
        setBoardError(null);
      } else {
        setBoardError(
          (body && body.error) || `The concierge board answered ${res.status}.`,
        );
      }
    } catch (e: any) {
      setBoardError(
        `Fleet cannot reach the concierge board (${e?.message || e}).`,
      );
    } finally {
      inFlight.current = false;
    }
  }, []);

  const running = (tasks || []).filter(t => t.state === 'running').length;
  const live = open || running > 0;

  useEffect(() => {
    refresh();
    const id = setInterval(
      () => {
        if (typeof document !== 'undefined' && document.hidden) return;
        refresh();
      },
      live ? pollMs : idlePollMs,
    );
    return () => clearInterval(id);
  }, [live, pollMs, idlePollMs, refresh]);

  const trimmed = goal.trim();
  const tooLong = trimmed.length > MAX_GOAL_CHARS;
  const canSend = !sending && trimmed.length > 0 && !tooLong;

  const send = async () => {
    if (!canSend) return;
    setSending(true);
    setNotice(null);
    try {
      const res = await callRef.current({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal: trimmed, url: url.trim(), by: 'fleet' }),
      });
      const body = await bodyOf(res);
      if (res.ok && body && !body.error) {
        setNotice({ ok: true, text: sentLine(body) });
        setGoal('');
        refresh();
      } else {
        setNotice({
          ok: false,
          text: (body && body.error) || `Refused (${res.status}).`,
        });
      }
    } catch (e: any) {
      setNotice({
        ok: false,
        text: `Not sent: Fleet cannot reach the concierge board (${
          e?.message || e
        }).`,
      });
    } finally {
      setSending(false);
    }
  };

  const newest = tasks && tasks.length ? tasks[0] : null;

  return (
    // crew#1017: "'concierge' pill misalignment". This was `top-36` (144px) while the Harv
    // chip above starts at 8.5rem (136px) and is ~30px tall -- the two pills OVERLAPPED by 22px
    // and the right rail read as debris, not a stack. The rail is one coordinate system now:
    // AgentJobs 96px, Harv 136px, concierge 176px, KeySync 216px -- an even 40px pitch.
    <div className="absolute top-[11rem] right-6 z-40 pointer-events-auto flex flex-col items-end gap-2 max-w-[92vw]">
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
        className="px-3 py-1.5 rounded-full bg-black/70 border border-white/15 backdrop-blur-md text-[11px] font-mono text-white/80 hover:text-white max-w-[92vw] truncate"
      >
        concierge{running ? ` · ${running} running` : ''}
        {!open && newest && newest.state === 'running' ? (
          <span className="ml-2 text-cyan-200/80">{headline(newest)}</span>
        ) : null}
      </button>
      {open ? (
        <div
          role="region"
          aria-label="concierge tasks"
          className="w-[400px] max-w-[92vw] max-h-[70vh] overflow-y-auto p-3 rounded-xl bg-black/80 border border-white/10 backdrop-blur-md text-white/85 text-[12px]"
        >
          <form
            onSubmit={e => {
              e.preventDefault();
              send();
            }}
          >
            <label
              className="block text-[10px] font-mono uppercase tracking-wider text-white/45 mb-1"
              htmlFor="concierge-goal"
            >
              Ask the concierge
            </label>
            <textarea
              id="concierge-goal"
              value={goal}
              onChange={e => setGoal(e.target.value)}
              rows={2}
              placeholder="Buy bytesync.com on Namecheap"
              className="w-full rounded-md bg-white/5 border border-white/10 p-2 text-[12px] text-white/90 placeholder-white/25"
            />
            <div className="flex items-center gap-2 mt-2">
              <label className="sr-only" htmlFor="concierge-url">
                Start at
              </label>
              <input
                id="concierge-url"
                value={url}
                onChange={e => setUrl(e.target.value)}
                placeholder="start at (optional URL)"
                className="flex-1 min-w-0 rounded-md bg-white/5 border border-white/10 px-2 py-1 text-[11px] font-mono placeholder-white/25"
              />
              <span
                className={`text-[10px] font-mono ${
                  tooLong ? 'text-rose-300' : 'text-white/30'
                }`}
                data-testid="concierge-count"
              >
                {trimmed.length}/{MAX_GOAL_CHARS}
              </span>
              <button
                type="submit"
                disabled={!canSend}
                className="px-3 py-1 rounded-md border border-cyan-400/40 bg-cyan-500/15 text-cyan-100 disabled:opacity-35"
              >
                {sending ? 'Sending…' : 'Send'}
              </button>
            </div>
            <p className="mt-1 text-[10px] text-white/35">
              Or say it: “concierge, …”. It opens your Chrome on the laptop and
              stops at any pay step.
            </p>
          </form>

          {notice ? (
            <div
              role="status"
              className={`mt-2 text-[11px] ${
                notice.ok ? 'text-emerald-300' : 'text-rose-300'
              }`}
            >
              {notice.text}
            </div>
          ) : null}

          <div className="mt-3 border-t border-white/10 pt-2">
            {boardError ? (
              <div role="alert" className="text-[11px] text-amber-300">
                {boardError}
              </div>
            ) : null}
            {tasks === null && !boardError ? (
              <div className="text-[11px] text-white/40">Reading tasks…</div>
            ) : null}
            {tasks !== null && tasks.length === 0 ? (
              <div className="text-[11px] text-white/40">
                No concierge tasks yet.
              </div>
            ) : null}
            <ul className="flex flex-col gap-2">
              {(tasks || []).map(t => (
                <li
                  key={t.task_id}
                  data-testid="concierge-task"
                  data-state={t.state}
                  className="rounded-md bg-white/[0.03] border border-white/5 p-2"
                >
                  <div className="flex items-start gap-2">
                    <span className="flex-1 break-words">{t.goal}</span>
                    <span
                      className={`px-1.5 py-0.5 rounded border text-[9px] font-mono uppercase ${
                        STATE[t.state]
                      }`}
                    >
                      {t.state === 'running' ? `step ${t.steps}` : t.outcome}
                    </span>
                  </div>
                  {t.state !== 'running' && t.summary ? (
                    <div className="mt-1 text-[11px] text-white/80 break-words">
                      {t.summary}
                    </div>
                  ) : null}
                  {t.found.length ? (
                    <ul className="mt-1 flex flex-col gap-0.5">
                      {t.found.map((f, i) => (
                        <li
                          key={i}
                          className="text-[11px] text-emerald-300 break-words"
                        >
                          ✓ {f}
                        </li>
                      ))}
                    </ul>
                  ) : null}
                  <ol
                    aria-label={`steps of ${t.task_id}`}
                    className="mt-1 flex flex-col gap-0.5 font-mono text-[10px]"
                  >
                    {t.events.slice(-6).map((e, i) => (
                      <li
                        key={`${e.step}-${i}`}
                        className={`break-words ${KIND[e.kind] || 'text-white/50'}`}
                      >
                        <span className="text-white/30">{e.kind}</span> {e.text}
                      </li>
                    ))}
                  </ol>
                  <div className="mt-1 flex gap-3 text-[10px] font-mono">
                    {t.url ? (
                      <a
                        href={t.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-cyan-300 hover:underline truncate max-w-[260px]"
                      >
                        {t.url.replace(/^https?:\/\//, '')}
                      </a>
                    ) : null}
                    {t.receipt ? (
                      <span className="text-white/35">receipt kept</span>
                    ) : null}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      ) : null}
    </div>
  );
}
