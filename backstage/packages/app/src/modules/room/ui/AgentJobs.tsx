/**
 * Agent jobs: give an agent a task from Fleet, then watch it go agent -> firewall -> PR -> merged.
 *
 * The backend (fleetview_backend/agent_jobs.py) dispatches .github/workflows/agent-sandbox.yml and
 * reads its runs back; GitHub is the only ledger, so a job started anywhere shows up here. This
 * panel is the founder's work surface on a phone, so every outcome is a sentence on screen:
 *   - a refusal shows the backend's own reason, and the typed task is KEPT so nothing is retyped;
 *   - a double tap is one request (the button is disabled while one is in flight, and the backend
 *     dedups too);
 *   - a board that cannot read GitHub says why instead of showing an empty list.
 * It polls while mounted, faster when open, never two polls at once, not while the tab is hidden,
 * and not at all once unmounted.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { clear, unreadable, useSignal, type Signal } from './attention';

export type Call = (init?: RequestInit) => Promise<Response>;

export type Job = {
  run_id: number | null;
  harness: string | null;
  task: string;
  by?: string | null;
  run_url: string | null;
  stage: string;
  state: 'running' | 'done' | 'failed';
  reason: string | null;
  pr: { number: number | null; url: string | null; state: string } | null;
  duplicate?: boolean;
};

export const MAX_TASK_CHARS = 4000; // agent_jobs.MAX_TASK_CHARS
export const HARNESSES = ['pi', 'claude-code'] as const; // agent_jobs.HARNESSES
export const PIPELINE = [
  'queued',
  'agent',
  'firewall',
  'open-pr',
  'pr',
  'merged',
] as const;

type Notice = { ok: boolean; text: string } | null;

const CURRENT: Record<Job['state'], string> = {
  running: 'bg-cyan-500/25 text-cyan-100 border-cyan-400/50 animate-pulse',
  done: 'bg-emerald-500/25 text-emerald-200 border-emerald-400/50',
  failed: 'bg-rose-500/25 text-rose-200 border-rose-400/50',
};

async function bodyOf(res: Response): Promise<any> {
  try {
    return await res.json();
  } catch {
    return null;
  }
}

/** What the founder reads after pressing Send. */
export function sentLine(status: number, job: Job): string {
  if (job.duplicate) return `Already running as run ${job.run_id}.`;
  if (!job.run_id || status === 202)
    return job.reason || 'Sent; GitHub has not listed the run yet.';
  return `Sent: run ${job.run_id}.`;
}

function StageChips({ job }: { job: Job }) {
  const at = PIPELINE.indexOf(job.stage as any);
  return (
    <div className="flex flex-wrap gap-1 mt-1" data-testid="agent-job-stages">
      {PIPELINE.map((s, i) => {
        const here = i === at;
        const past = at >= 0 && i < at;
        let cls = 'text-white/60 border-white/5';
        if (past) cls = 'text-white/55 border-white/15';
        if (here) cls = CURRENT[job.state];
        return (
          <span
            key={s}
            data-stage={s}
            aria-current={here ? 'step' : undefined}
            className={`px-1.5 py-0.5 rounded border text-[12px] font-mono uppercase tracking-wider ${cls}`}
          >
            {s}
          </span>
        );
      })}
      {at < 0 ? (
        // cancelled, closed, failed, done: a terminal stage outside the happy path.
        <span
          data-stage={job.stage}
          aria-current="step"
          className={`px-1.5 py-0.5 rounded border text-[12px] font-mono uppercase tracking-wider ${CURRENT.failed}`}
        >
          {job.stage}
        </span>
      ) : null}
    </div>
  );
}

/** The rail's view: a failed job needs a person; a running one is just work happening. */
export function jobsSignal(jobs: Job[] | null, err: string | null): Signal {
  if (err) return unreadable('jobs');
  const failed = (jobs || []).filter(j => j.state === 'failed');
  if (!failed.length) return clear('jobs');
  const why = failed[0].reason ? ` — ${failed[0].reason}` : '';
  return {
    source: 'jobs',
    tier: 'caution',
    summary: `jobs · ${failed.length} failed${failed.length === 1 ? why : ''}`,
  };
}

export default function AgentJobs({
  call,
  onSignal,
  pollMs = 20_000,
  idlePollMs = 60_000,
}: {
  call: Call;
  /** Report this panel's attention tier to the rail (attention.ts). */
  onSignal?: (s: Signal) => void;
  pollMs?: number;
  idlePollMs?: number;
}) {
  const [open, setOpen] = useState(false);
  const [task, setTask] = useState('');
  const [harness, setHarness] = useState<string>('pi');
  const [sending, setSending] = useState(false);
  const [notice, setNotice] = useState<Notice>(null);
  const [jobs, setJobs] = useState<Job[] | null>(null);
  const [boardError, setBoardError] = useState<string | null>(null);

  // The caller's closure changes every render; the poll must not restart because of it.
  const callRef = useRef(call);
  callRef.current = call;
  const inFlight = useRef(false);

  const refresh = useCallback(async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    try {
      const res = await callRef.current();
      const body = await bodyOf(res);
      if (body && Array.isArray(body.jobs) && body.available !== false) {
        setJobs(body.jobs);
        setBoardError(null);
      } else {
        setBoardError(
          (body && body.error) || `The job board answered ${res.status}.`,
        );
      }
    } catch (e: any) {
      setBoardError(`Fleet cannot reach the job board (${e?.message || e}).`);
    } finally {
      inFlight.current = false;
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(
      () => {
        if (typeof document !== 'undefined' && document.hidden) return;
        refresh();
      },
      open ? pollMs : idlePollMs,
    );
    return () => clearInterval(id);
  }, [open, pollMs, idlePollMs, refresh]);

  const trimmed = task.trim();
  const tooLong = trimmed.length > MAX_TASK_CHARS;
  const canSend = !sending && trimmed.length > 0 && !tooLong;

  const send = async () => {
    // A second tap finds the button disabled: React flushes each tap before the next.
    if (!canSend) return;
    setSending(true);
    setNotice(null);
    try {
      const res = await callRef.current({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task: trimmed, harness, by: 'fleet' }),
      });
      const body = await bodyOf(res);
      if (res.ok && body && !body.error) {
        setNotice({ ok: true, text: sentLine(res.status, body) });
        setTask('');
        refresh();
      } else {
        // Refused: say why, keep the task so the founder edits instead of retyping.
        setNotice({
          ok: false,
          text: (body && body.error) || `Refused (${res.status}).`,
        });
      }
    } catch (e: any) {
      setNotice({
        ok: false,
        text: `Not sent: Fleet cannot reach the job board (${
          e?.message || e
        }).`,
      });
    } finally {
      setSending(false);
    }
  };

  const running = (jobs || []).filter(j => j.state === 'running').length;

  useSignal(onSignal, jobsSignal(jobs, boardError));

  return (
    <div className="pointer-events-auto flex flex-col items-end gap-2 max-w-[92vw]">
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
        className="px-3 py-1.5 rounded-full bg-black/70 border border-white/15 backdrop-blur-md text-[12px] font-mono text-white/80 hover:text-white"
      >
        agent jobs{running ? ` · ${running} running` : ''}
      </button>
      {open ? (
        <div
          role="region"
          aria-label="agent jobs"
          className="w-[380px] max-w-[92vw] max-h-[70vh] overflow-y-auto p-3 rounded-xl bg-black/80 border border-white/10 backdrop-blur-md text-white/85 text-[12px]"
        >
          <form
            onSubmit={e => {
              e.preventDefault();
              send();
            }}
          >
            <label
              className="block text-[12px] font-mono uppercase tracking-wider text-white/60 mb-1"
              htmlFor="agent-job-task"
            >
              Give an agent a job
            </label>
            <textarea
              id="agent-job-task"
              value={task}
              onChange={e => setTask(e.target.value)}
              rows={3}
              placeholder="Fix the typo in docs/index.md"
              className="w-full rounded-md bg-white/5 border border-white/10 p-2 text-[12px] text-white/90 placeholder-white/25"
            />
            <div className="flex items-center gap-2 mt-2">
              <label className="sr-only" htmlFor="agent-job-harness">
                Harness
              </label>
              <select
                id="agent-job-harness"
                value={harness}
                onChange={e => setHarness(e.target.value)}
                className="rounded-md bg-white/5 border border-white/10 px-2 py-1 text-[12px] font-mono"
              >
                {HARNESSES.map(h => (
                  <option key={h} value={h}>
                    {h}
                  </option>
                ))}
              </select>
              <span
                className={`text-[12px] font-mono ${
                  tooLong ? 'text-rose-300' : 'text-white/60'
                }`}
                data-testid="agent-job-count"
              >
                {trimmed.length}/{MAX_TASK_CHARS}
              </span>
              <button
                type="submit"
                disabled={!canSend}
                className="ml-auto px-3 py-1 rounded-md border border-cyan-400/40 bg-cyan-500/15 text-cyan-100 disabled:opacity-35"
              >
                {sending ? 'Sending…' : 'Send'}
              </button>
            </div>
            <p className="mt-1 text-[12px] text-white/60">
              The task is published on the public run page. Name secrets by env
              var, never paste them.
            </p>
          </form>

          {notice ? (
            <div
              role="status"
              className={`mt-2 text-[12px] ${
                notice.ok ? 'text-emerald-300' : 'text-rose-300'
              }`}
            >
              {notice.text}
            </div>
          ) : null}

          <div className="mt-3 border-t border-white/10 pt-2">
            {boardError ? (
              <div role="alert" className="text-[12px] text-amber-300">
                {boardError}
              </div>
            ) : null}
            {jobs === null && !boardError ? (
              <div className="text-[12px] text-white/60">Reading jobs…</div>
            ) : null}
            {jobs !== null && jobs.length === 0 ? (
              <div className="text-[12px] text-white/60">
                No agent jobs yet.
              </div>
            ) : null}
            <ul className="flex flex-col gap-2">
              {(jobs || []).map(j => (
                <li
                  key={j.run_id ?? j.task}
                  data-testid="agent-job"
                  data-state={j.state}
                  className="rounded-md bg-white/[0.03] border border-white/5 p-2"
                >
                  <div className="flex items-start gap-2">
                    <span className="flex-1 break-words">{j.task}</span>
                    <span className="text-[12px] font-mono text-white/60">
                      {j.harness || '?'}
                    </span>
                  </div>
                  <StageChips job={j} />
                  {j.reason ? (
                    <div className="mt-1 text-[12px] text-rose-200/90 break-words">
                      {j.reason}
                    </div>
                  ) : null}
                  <div className="mt-1 flex gap-3 text-[12px] font-mono">
                    {j.run_url ? (
                      <a
                        href={j.run_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-cyan-300 hover:underline"
                      >
                        run {j.run_id}
                      </a>
                    ) : null}
                    {j.pr && j.pr.url ? (
                      <a
                        href={j.pr.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-cyan-300 hover:underline"
                      >
                        PR #{j.pr.number} ({j.pr.state})
                      </a>
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
