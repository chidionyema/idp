// The Face's command deck, as pure functions: what the estate can do (GET /voice/intents), how a
// typed query ranks it, and how one command is run through the SAME door the voice uses
// (POST /voice/intent), so a tap and a spoken sentence cannot differ in what they are allowed to do.
//
// CONFIRMATION IS THE BACKEND'S, NOT THE DECK'S. A non-read-only intent answers
// `pending_confirmation` and waits for a yes on the same session; the deck only relays that
// question and the answer. It never decides a command is safe, and it never sends "yes" on its own.
import type { IntentResult } from './intentCue';
import { parseIntentResult } from './intentCue';

export type Command = { name: string; description: string; read_only: boolean };

export type Post = (body: { text: string; session_id: string }) => Promise<{ status: number; body: unknown }>;

export type CommandOutcome =
  | { kind: 'result'; result: IntentResult }
  | { kind: 'error'; error: string };

export function parseCatalogue(body: unknown): Command[] {
  const list = (body as { intents?: unknown } | null)?.intents;
  if (!Array.isArray(list)) return [];
  return list
    .filter(
      (c): c is Command =>
        typeof c === 'object' && c !== null && typeof (c as Command).name === 'string' && (c as Command).name !== '',
    )
    .map(c => ({
      name: c.name,
      description: typeof c.description === 'string' ? c.description : '',
      read_only: c.read_only === true,
    }))
    .sort((a, b) => a.name.localeCompare(b.name));
}

/** Exact name, then name prefix, then name substring, then description substring; empty query = all. */
export function rankCommands(commands: Command[], query: string): Command[] {
  const q = query.trim().toLowerCase();
  if (!q) return [...commands].sort((a, b) => a.name.localeCompare(b.name));
  const score = (c: Command): number => {
    const n = c.name.toLowerCase();
    if (n === q) return 0;
    if (n.startsWith(q)) return 1;
    if (n.includes(q)) return 2;
    if (c.description.toLowerCase().includes(q)) return 3;
    return -1;
  };
  return commands
    .map(c => ({ c, s: score(c) }))
    .filter(x => x.s >= 0)
    .sort((a, b) => a.s - b.s || a.c.name.localeCompare(b.c.name))
    .map(x => x.c);
}

async function send(post: Post, text: string, session: string): Promise<CommandOutcome> {
  try {
    const r = await post({ text, session_id: session });
    if (r.status === 204) return { kind: 'error', error: `The estate did not recognise "${text}".` };
    const parsed = parseIntentResult(r.body);
    if (r.status >= 200 && r.status < 300 && parsed) return { kind: 'result', result: parsed };
    return { kind: 'error', error: `The estate answered ${r.status} and no result.` };
  } catch (e) {
    return { kind: 'error', error: String((e as Error)?.message ?? e) };
  }
}

/** Run an intent by name. The matcher keys on the name's words, so the name itself is the utterance. */
export function runCommand(post: Post, name: string, session: string): Promise<CommandOutcome> {
  return send(post, name, session);
}

/** Answer the backend's pending_confirmation on the same session. */
export function confirmCommand(post: Post, session: string, yes: boolean): Promise<CommandOutcome> {
  return send(post, yes ? 'yes' : 'no', session);
}

/** "Give an agent a job" is the voice's own phrase for the agent door; the backend reads it back. */
export function runAgentJob(post: Post, task: string, session: string): Promise<CommandOutcome> {
  return send(post, `give an agent a job: ${task}`, session);
}
