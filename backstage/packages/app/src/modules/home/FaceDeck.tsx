/**
 * THE COMMAND DECK: everything the estate can do, from the Face. Three tabs over one door.
 *   Commands  every committed intent (GET /voice/intents), filtered as you type, run through
 *             POST /voice/intent -- the voice's own door, so a tap and a sentence share one gate.
 *   Agents    the jobs the estate is tracking (the same board /fleet reads), and a box to launch one.
 *   Persona   the avatar the face wears (swapped live) and the voice it speaks with.
 *
 * Nothing here decides a command is safe. A risky intent answers `pending_confirmation`; the deck
 * shows the backend's own question with Confirm / Cancel and sends the answer on the same session.
 * Closed by default and fetches nothing until opened.
 */
import { useCallback, useEffect, useMemo, useState, type CSSProperties } from 'react';
import { fetchApiRef, useApi } from '@backstage/frontend-plugin-api';
import {
  confirmCommand,
  parseCatalogue,
  rankCommands,
  runAgentJob,
  runCommand,
  type Command,
  type CommandOutcome,
  type Post,
} from './faceCommands';
import { AVATARS, customAvatar, parseAvatarUrl, readAvatar, saveAvatar, type Avatar } from './faceAvatars';
import { getActiveFace } from './faceEngine';
import type { LoadedJobs } from './useAgentJobs';

const FLEETVIEW = 'plugin://proxy/fleetview';

type Tab = 'commands' | 'agents' | 'persona';
type Catalogue = { state: 'loading' } | { state: 'error'; error: string } | { state: 'ready'; commands: Command[] };

export interface DeckVoice {
  current: { engine: string; voice: string };
  catalogue?: Record<string, string[]> | null;
  selectVoice: (engine: string, voice: string) => Promise<string>;
}

const glass: CSSProperties = {
  background: 'rgba(11,14,20,0.82)',
  border: '1px solid rgba(232,237,245,0.16)',
  borderRadius: 14,
  backdropFilter: 'blur(14px)',
  color: '#e8edf5',
  pointerEvents: 'auto',
};
const field: CSSProperties = {
  background: 'rgba(232,237,245,0.06)',
  color: '#e8edf5',
  border: '1px solid rgba(232,237,245,0.22)',
  borderRadius: 8,
  padding: '6px 10px',
  fontSize: 13,
};
const btn = (primary = false): CSSProperties => ({
  ...field,
  cursor: 'pointer',
  background: primary ? 'rgba(0,240,255,0.16)' : field.background,
  borderColor: primary ? 'rgba(0,240,255,0.5)' : 'rgba(232,237,245,0.22)',
});

function newSession(): string {
  try {
    return `deck-${crypto.randomUUID()}`;
  } catch {
    return `deck-${Date.now()}-${Math.floor(Math.random() * 1e6)}`;
  }
}

export default function FaceDeck({ voice, jobs }: { voice: DeckVoice; jobs: LoadedJobs }) {
  const fetchApi = useApi(fetchApiRef);
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState<Tab>('commands');
  const session = useMemo(newSession, []);

  const post: Post = useCallback(
    async body => {
      const r = await fetchApi.fetch(`${FLEETVIEW}/voice/intent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      return { status: r.status, body: r.status === 204 ? null : await r.json().catch(() => null) };
    },
    [fetchApi],
  );

  return (
    <div style={{ position: 'absolute', right: 16, bottom: 'calc(env(safe-area-inset-bottom, 0px) + 16px)', zIndex: 5 }}>
      {!open && (
        <button type="button" data-testid="face-deck-open" style={{ ...btn(true), ...glass, padding: '8px 14px' }} onClick={() => setOpen(true)}>
          Deck
        </button>
      )}
      {open && (
        <section
          data-testid="face-deck"
          aria-label="Command deck"
          style={{ ...glass, width: 'min(420px, calc(100vw - 32px))', maxHeight: '60vh', display: 'grid', gridTemplateRows: 'auto 1fr', overflow: 'hidden' }}
        >
          <div style={{ display: 'flex', gap: 6, padding: 8, borderBottom: '1px solid rgba(232,237,245,0.12)' }} role="tablist">
            {(['commands', 'agents', 'persona'] as Tab[]).map(t => (
              <button
                key={t}
                type="button"
                role="tab"
                aria-selected={tab === t}
                data-testid={`face-deck-tab-${t}`}
                style={{ ...btn(tab === t), textTransform: 'capitalize' }}
                onClick={() => setTab(t)}
              >
                {t}
              </button>
            ))}
            <span style={{ flex: 1 }} />
            <button type="button" aria-label="Close deck" style={btn()} onClick={() => setOpen(false)}>
              ✕
            </button>
          </div>
          <div style={{ overflow: 'auto', padding: 10 }}>
            {tab === 'commands' && <CommandsTab post={post} session={session} fetchApi={fetchApi} />}
            {tab === 'agents' && <AgentsTab post={post} session={session} jobs={jobs} />}
            {tab === 'persona' && <PersonaTab voice={voice} />}
          </div>
        </section>
      )}
    </div>
  );
}

/** One outcome, and Confirm/Cancel only when the backend is waiting on a yes. */
function Outcome({ out, onAnswer, busy }: { out: CommandOutcome | null; onAnswer: (yes: boolean) => void; busy: boolean }) {
  if (!out) return null;
  if (out.kind === 'error') {
    return (
      <div role="alert" data-testid="face-deck-error" style={{ color: '#ff8aa8', fontSize: 12, marginTop: 8 }}>
        {out.error}
      </div>
    );
  }
  const pending = out.result.status === 'pending_confirmation';
  return (
    <div data-testid="face-deck-result" data-status={out.result.status} style={{ marginTop: 8, fontSize: 13, lineHeight: 1.45 }}>
      <div style={{ opacity: 0.6, fontSize: 11 }}>
        {out.result.intent} · {out.result.status}
      </div>
      <div style={{ whiteSpace: 'pre-wrap' }}>{out.result.text}</div>
      {pending && (
        <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
          <button type="button" data-testid="face-deck-confirm" disabled={busy} style={btn(true)} onClick={() => onAnswer(true)}>
            Confirm
          </button>
          <button type="button" data-testid="face-deck-cancel" disabled={busy} style={btn()} onClick={() => onAnswer(false)}>
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}

function useAnswer(post: Post, session: string) {
  const [out, setOut] = useState<CommandOutcome | null>(null);
  const [busy, setBusy] = useState(false);
  const run = useCallback(async (go: () => Promise<CommandOutcome>) => {
    setBusy(true);
    setOut(null);
    setOut(await go());
    setBusy(false);
  }, []);
  const answer = useCallback((yes: boolean) => run(() => confirmCommand(post, session, yes)), [post, session, run]);
  return { out, busy, run, answer };
}

function CommandsTab({ post, session, fetchApi }: { post: Post; session: string; fetchApi: { fetch: (url: string) => Promise<Response> } }) {
  const [cat, setCat] = useState<Catalogue>({ state: 'loading' });
  const [q, setQ] = useState('');
  const { out, busy, run, answer } = useAnswer(post, session);

  useEffect(() => {
    let gone = false;
    (async () => {
      try {
        const r = await fetchApi.fetch(`${FLEETVIEW}/voice/intents`);
        const commands = parseCatalogue(await r.json().catch(() => null));
        if (gone) return;
        setCat(r.ok ? { state: 'ready', commands } : { state: 'error', error: `The catalogue answered ${r.status}.` });
      } catch (e) {
        if (!gone) setCat({ state: 'error', error: `The catalogue could not be reached: ${String((e as Error)?.message ?? e)}` });
      }
    })();
    return () => {
      gone = true;
    };
  }, [fetchApi]);

  if (cat.state === 'loading') return <div role="status">Reading what the estate can do…</div>;
  if (cat.state === 'error') return <div role="alert" data-testid="face-deck-error">{cat.error}</div>;
  const shown = rankCommands(cat.commands, q).slice(0, 40);
  return (
    <div>
      <input
        data-testid="face-deck-filter"
        aria-label="Filter commands"
        placeholder={`Filter ${cat.commands.length} commands`}
        value={q}
        onChange={e => setQ(e.target.value)}
        style={{ ...field, width: '100%', boxSizing: 'border-box' }}
      />
      <ul style={{ listStyle: 'none', margin: '8px 0 0', padding: 0, display: 'grid', gap: 4 }}>
        {shown.map(c => (
          <li key={c.name} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 13 }}>
                {c.name} {!c.read_only && <span title="Asks before running" style={{ color: '#ffb000', fontSize: 11 }}>asks first</span>}
              </div>
              <div style={{ fontSize: 11, opacity: 0.6, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{c.description}</div>
            </div>
            <button type="button" data-testid={`face-deck-run-${c.name}`} disabled={busy} style={btn()} onClick={() => run(() => runCommand(post, c.name, session))}>
              Run
            </button>
          </li>
        ))}
        {shown.length === 0 && <li style={{ opacity: 0.6, fontSize: 12 }}>Nothing matches “{q}”.</li>}
      </ul>
      <Outcome out={out} onAnswer={answer} busy={busy} />
    </div>
  );
}

function AgentsTab({ post, session, jobs }: { post: Post; session: string; jobs: LoadedJobs }) {
  const [task, setTask] = useState('');
  const { out, busy, run, answer } = useAnswer(post, session);
  const mark = { running: '●', done: '✓', failed: '✕' } as const;
  return (
    <div>
      <div style={{ display: 'flex', gap: 8 }}>
        <input
          data-testid="face-deck-task"
          aria-label="Task for an agent"
          placeholder="Give an agent a job…"
          value={task}
          onChange={e => setTask(e.target.value)}
          style={{ ...field, flex: 1, minWidth: 0 }}
        />
        <button type="button" data-testid="face-deck-launch" disabled={busy || !task.trim()} style={btn(true)} onClick={() => run(() => runAgentJob(post, task.trim(), session))}>
          Send
        </button>
      </div>
      <Outcome out={out} onAnswer={answer} busy={busy} />
      <div style={{ marginTop: 12, fontSize: 12 }}>
        {jobs.state === 'loading' && <div role="status">Reading the agent board…</div>}
        {jobs.state === 'unavailable' && <div data-testid="face-deck-jobs-unavailable">Agent board unavailable: {jobs.error}</div>}
        {jobs.state === 'ready' && jobs.jobs.length === 0 && <div style={{ opacity: 0.6 }}>No agent jobs on the board.</div>}
        {jobs.state === 'ready' &&
          [...jobs.jobs]
            .sort((a, b) => Number(b.state === 'running') - Number(a.state === 'running') || b.run_id - a.run_id)
            .slice(0, 12)
            .map(j => (
              <div key={j.run_id} data-testid="face-deck-job" style={{ padding: '3px 0', opacity: j.state === 'running' ? 1 : 0.65 }}>
                {mark[j.state]} {j.task} — {j.state === 'running' ? j.stage : j.state}
                {j.state === 'failed' && j.reason ? `: ${j.reason}` : ''}
                {j.pr?.url ? (
                  <>
                    {' '}
                    <a href={j.pr.url} target="_blank" rel="noreferrer" style={{ color: '#00f0ff' }}>
                      PR {j.pr.number}
                    </a>
                  </>
                ) : null}
              </div>
            ))}
      </div>
    </div>
  );
}

function PersonaTab({ voice }: { voice: DeckVoice }) {
  const store = typeof localStorage !== 'undefined' ? localStorage : null;
  const [avatar, setAvatar] = useState<Avatar>(() => readAvatar(store, typeof location !== 'undefined' ? location.origin : undefined));
  const [url, setUrl] = useState('');
  const [note, setNote] = useState('');
  const [voiceNote, setVoiceNote] = useState('');

  const apply = async (a: Avatar) => {
    const face = getActiveFace();
    if (!face) {
      setNote('The face is not on screen, so there is nothing to change.');
      return;
    }
    setNote(`Loading ${a.label}…`);
    try {
      await face.setAvatar(a);
      setAvatar(a);
      setNote(saveAvatar(store, a) ? `Now wearing ${a.label}.` : `Now wearing ${a.label} (this browser would not remember it).`);
    } catch (e) {
      setNote(`Could not load ${a.label}: ${String((e as Error)?.message ?? e)}. The previous avatar stays.`);
    }
  };
  const useCustom = () => {
    const parsed = parseAvatarUrl(url, typeof location !== 'undefined' ? location.origin : undefined);
    if (!parsed) {
      setNote('That is not a usable avatar: it must be an http(s) link to a .glb file.');
      return;
    }
    apply(customAvatar(parsed));
  };

  const voices = Object.entries(voice.catalogue ?? {}).flatMap(([eng, names]) => names.map(n => ({ engine: eng, voice: n })));
  return (
    <div style={{ display: 'grid', gap: 14, fontSize: 13 }}>
      <div>
        <div style={{ opacity: 0.6, fontSize: 11, marginBottom: 4 }}>Avatar</div>
        <div style={{ display: 'grid', gap: 6 }}>
          {AVATARS.map(a => (
            <button key={a.id} type="button" data-testid={`face-deck-avatar-${a.id}`} aria-pressed={avatar.id === a.id} style={{ ...btn(avatar.id === a.id), textAlign: 'left' }} onClick={() => apply(a)}>
              {a.label} <span style={{ opacity: 0.55, fontSize: 11 }}>· {a.licence}</span>
            </button>
          ))}
        </div>
        <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
          <input data-testid="face-deck-avatar-url" aria-label="Avatar GLB link" placeholder="https://…/avatar.glb" value={url} onChange={e => setUrl(e.target.value)} style={{ ...field, flex: 1, minWidth: 0 }} />
          <button type="button" data-testid="face-deck-avatar-use" style={btn()} onClick={useCustom}>
            Use
          </button>
        </div>
        {note && (
          <div role="status" data-testid="face-deck-avatar-note" style={{ fontSize: 11, opacity: 0.7, marginTop: 6 }}>
            {note}
          </div>
        )}
      </div>
      <div>
        <div style={{ opacity: 0.6, fontSize: 11, marginBottom: 4 }}>Voice</div>
        {voices.length > 1 ? (
          <select
            data-testid="face-deck-voice"
            aria-label="Deck voice"
            value={`${voice.current.engine}/${voice.current.voice}`}
            onChange={async e => {
              const [eng, ...rest] = e.target.value.split('/');
              setVoiceNote(await voice.selectVoice(eng, rest.join('/')));
            }}
            style={{ ...field, width: '100%' }}
          >
            {voices.map(o => (
              <option key={`${o.engine}/${o.voice}`} value={`${o.engine}/${o.voice}`}>
                {o.voice} ({o.engine})
              </option>
            ))}
          </select>
        ) : (
          <div style={{ opacity: 0.7 }}>This voice engine has one voice: {voice.current.voice}.</div>
        )}
        {voiceNote && <div style={{ fontSize: 11, opacity: 0.7, marginTop: 6 }}>{voiceNote}</div>}
      </div>
    </div>
  );
}
