import {
  confirmCommand,
  parseCatalogue,
  rankCommands,
  runAgentJob,
  runCommand,
  type Command,
  type Post,
} from './faceCommands';

const cat: Command[] = [
  { name: 'ci-status', description: 'Show CI state of a pull request', read_only: true },
  { name: 'flux-reconcile', description: 'Force Flux to reconcile', read_only: false },
  { name: 'flux-status', description: 'Flux health', read_only: true },
  { name: 'cost-today', description: 'What the router spent today', read_only: true },
];

const ok = (intent: string, status: string, text: string) => ({
  kind: 'intent_result',
  intent,
  status,
  text,
  visual: { cue: 'pulse', target: 'fleet', severity: 'info' },
  ticket: null,
});

describe('parseCatalogue', () => {
  it('keeps well-formed rows, sorts, and tolerates junk', () => {
    const rows = parseCatalogue({
      intents: [{ name: 'b', description: 'x', read_only: true }, { name: 'a' }, 7, null, { name: '' }],
    });
    expect(rows.map(r => r.name)).toEqual(['a', 'b']);
    expect(rows[0]).toEqual({ name: 'a', description: '', read_only: false });
  });
  it('is empty for a body with no list', () => {
    expect(parseCatalogue({})).toEqual([]);
    expect(parseCatalogue(null)).toEqual([]);
  });
});

describe('rankCommands', () => {
  it('returns everything sorted for an empty query', () => {
    expect(rankCommands(cat, '  ').map(c => c.name)).toEqual([
      'ci-status',
      'cost-today',
      'flux-reconcile',
      'flux-status',
    ]);
  });
  it('ranks exact, then prefix, then substring, then description', () => {
    expect(rankCommands(cat, 'flux').map(c => c.name)).toEqual(['flux-reconcile', 'flux-status']);
    expect(rankCommands(cat, 'status').map(c => c.name)).toEqual(['ci-status', 'flux-status']);
    expect(rankCommands(cat, 'spent').map(c => c.name)).toEqual(['cost-today']);
    expect(rankCommands(cat, 'ci-status')[0].name).toBe('ci-status');
  });
  it('is empty when nothing matches', () => {
    expect(rankCommands(cat, 'zzz')).toEqual([]);
  });
});

describe('running commands', () => {
  it('posts the name and returns the parsed result', async () => {
    const post: Post = jest.fn(async () => ({ status: 200, body: ok('ci-status', 'ok', 'green') }));
    const out = await runCommand(post, 'ci-status', 's1');
    expect(post).toHaveBeenCalledWith({ text: 'ci-status', session_id: 's1' });
    expect(out.kind === 'result' && out.result.text).toBe('green');
  });
  it('hands back a pending confirmation unresolved, and sends yes/no only when told', async () => {
    const post: Post = jest
      .fn()
      .mockResolvedValueOnce({ status: 200, body: ok('flux-reconcile', 'pending_confirmation', 'Run it?') })
      .mockResolvedValueOnce({ status: 200, body: ok('flux-reconcile', 'ok', 'done') });
    const first = await runCommand(post, 'flux-reconcile', 's2');
    expect(first.kind === 'result' && first.result.status).toBe('pending_confirmation');
    expect(post).toHaveBeenCalledTimes(1);
    const second = await confirmCommand(post, 's2', true);
    expect(post).toHaveBeenLastCalledWith({ text: 'yes', session_id: 's2' });
    expect(second.kind === 'result' && second.result.status).toBe('ok');
  });
  it('names a 204 and a network failure as errors, never throws', async () => {
    const a = await runCommand(async () => ({ status: 204, body: null }), 'x', 's');
    expect(a.kind === 'error' && a.error).toMatch(/did not recognise/);
    const b = await runCommand(
      async () => {
        throw new Error('offline');
      },
      'x',
      's',
    );
    expect(b).toEqual({ kind: 'error', error: 'offline' });
    const c = await runCommand(async () => ({ status: 500, body: {} }), 'x', 's');
    expect(c.kind).toBe('error');
  });
  it('sends an agent job in the voice phrase', async () => {
    const post: Post = jest.fn(async () => ({ status: 200, body: ok('agent-job', 'pending_confirmation', 'Send?') }));
    await runAgentJob(post, 'fix the thing', 's3');
    expect(post).toHaveBeenCalledWith({ text: 'give an agent a job: fix the thing', session_id: 's3' });
  });
});
