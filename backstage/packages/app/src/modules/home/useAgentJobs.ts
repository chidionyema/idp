// The face follows the agents it sends. "Give an agent a job: <task>" (voice_intents.py) submits a
// job after a spoken read-back and a yes; until now the face spoke "Sent. Run 123." and then went
// blind to it -- /fleet could watch the job, the face could not. This polls the same
// `/fleetview/agent-jobs` board /fleet reads (agent_jobs.list_jobs), shows what is running, and
// SAYS when a job ends, so the founder who launched work by voice hears how it went.
//
// HONESTY RULES (the estate's section 3): a board that cannot be read is `unavailable` with its
// reason, never an empty list wearing the face of "nothing is running". An announcement is made
// only for a job this page watched change state -- the first poll after a page load is a baseline,
// not news, so opening the face never replays every old job aloud.
import { useEffect, useRef, useState } from 'react';
import { fetchApiRef, useApi } from '@backstage/frontend-plugin-api';

export type AgentJob = {
  run_id: number;
  task: string;
  stage: string;
  state: 'running' | 'done' | 'failed';
  reason?: string | null;
  pr?: { number?: number | null; url?: string | null; state?: string } | null;
};

export type LoadedJobs =
  | { state: 'loading' }
  | { state: 'unavailable'; error: string }
  | { state: 'ready'; jobs: AgentJob[] };

// A running job moves in minutes; an idle board is only checked at the home heartbeat. The board
// is a GitHub read behind one hourly token budget, so the fast poll runs only while something runs.
export const FAST_MS = 10_000;
export const SLOW_MS = 60_000;

const STATES = ['running', 'done', 'failed'];

export function parseJobs(status: number, body: unknown): LoadedJobs {
  const b = (typeof body === 'object' && body !== null ? body : {}) as Record<string, unknown>;
  if (status < 200 || status >= 300 || b.available === false) {
    const why = typeof b.error === 'string' && b.error ? b.error : `agent-jobs answered ${status}`;
    return { state: 'unavailable', error: why };
  }
  if (!Array.isArray(b.jobs)) return { state: 'unavailable', error: 'agent-jobs sent no job list' };
  const jobs = b.jobs.filter(
    (j): j is AgentJob =>
      typeof j === 'object' &&
      j !== null &&
      typeof (j as AgentJob).run_id === 'number' &&
      typeof (j as AgentJob).task === 'string' &&
      STATES.includes((j as AgentJob).state),
  );
  return { state: 'ready', jobs };
}

/** What a job ending is called aloud. Short: it is spoken over whatever the founder is doing. */
export function sentenceFor(job: AgentJob): string {
  const task = job.task.length > 80 ? `${job.task.slice(0, 79)}…` : job.task;
  if (job.state === 'done') {
    return job.pr?.number
      ? `The agent finished: ${task}. Pull request ${job.pr.number} is merged.`
      : `The agent finished: ${task}.`;
  }
  return `The agent failed: ${task}. ${job.reason ?? `It stopped at ${job.stage}.`}`;
}

/**
 * The jobs that went running -> done|failed between two polls. `prev` is run_id -> state of the
 * last poll; a job absent from `prev` was never seen running here, so it is not announced.
 */
export function finishedSince(prev: Map<number, AgentJob['state']>, jobs: AgentJob[]): AgentJob[] {
  return jobs.filter((j) => j.state !== 'running' && prev.get(j.run_id) === 'running');
}

export function useAgentJobs(speak?: (text: string) => void): LoadedJobs {
  const fetchApi = useApi(fetchApiRef);
  const fetchRef = useRef(fetchApi);
  fetchRef.current = fetchApi;
  const speakRef = useRef(speak);
  speakRef.current = speak;
  const [loaded, setLoaded] = useState<LoadedJobs>({ state: 'loading' });

  useEffect(() => {
    let cancelled = false;
    let inFlight = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const seen = new Map<number, AgentJob['state']>();

    const tick = async () => {
      if (inFlight) return;
      inFlight = true;
      let next: LoadedJobs;
      try {
        const r = await fetchRef.current.fetch('plugin://proxy/fleetview/agent-jobs');
        next = parseJobs(r.status, await r.json().catch(() => ({})));
      } catch (e) {
        next = { state: 'unavailable', error: String((e as Error)?.message ?? e) };
      } finally {
        inFlight = false;
      }
      if (cancelled) return;
      setLoaded(next);
      if (next.state === 'ready') {
        for (const j of finishedSince(seen, next.jobs)) speakRef.current?.(sentenceFor(j));
        for (const j of next.jobs) seen.set(j.run_id, j.state);
      }
      const busy = next.state === 'ready' && next.jobs.some((j) => j.state === 'running');
      timer = setTimeout(tick, busy ? FAST_MS : SLOW_MS);
    };
    tick();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, []);

  return loaded;
}
