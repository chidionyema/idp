import { finishedSince, parseJobs, sentenceFor, type AgentJob } from './useAgentJobs';

const job = (over: Partial<AgentJob> = {}): AgentJob => ({
  run_id: 1,
  task: 'add a README line',
  stage: 'agent',
  state: 'running',
  ...over,
});

describe('parseJobs', () => {
  it('reads a ready board', () => {
    expect(parseJobs(200, { available: true, jobs: [job()] })).toEqual({ state: 'ready', jobs: [job()] });
  });
  it('an empty board is ready and empty, a broken one is unavailable with its reason', () => {
    expect(parseJobs(200, { available: true, jobs: [] })).toEqual({ state: 'ready', jobs: [] });
    expect(parseJobs(502, { available: false, error: 'github unreachable', jobs: [] })).toEqual({
      state: 'unavailable',
      error: 'github unreachable',
    });
    expect(parseJobs(503, null)).toEqual({ state: 'unavailable', error: 'agent-jobs answered 503' });
  });
  it('drops rows it cannot trust instead of rendering them', () => {
    const r = parseJobs(200, { available: true, jobs: [job(), { run_id: 'x' }, { run_id: 2, task: 't', state: 'weird' }] });
    expect(r).toEqual({ state: 'ready', jobs: [job()] });
  });
});

describe('finishedSince', () => {
  it('announces only a job it watched run and then end', () => {
    const prev = new Map<number, AgentJob['state']>([[1, 'running'], [2, 'done']]);
    const out = finishedSince(prev, [job({ run_id: 1, state: 'done' }), job({ run_id: 2, state: 'done' }), job({ run_id: 3, state: 'failed' })]);
    expect(out.map((j) => j.run_id)).toEqual([1]);
  });
  it('the first poll is a baseline: nothing is announced', () => {
    expect(finishedSince(new Map(), [job({ state: 'done' })])).toEqual([]);
  });
  it('a job still running is not announced', () => {
    expect(finishedSince(new Map([[1, 'running']]), [job()])).toEqual([]);
  });
});

describe('sentenceFor', () => {
  it('names the merged PR on success and the reason on failure', () => {
    expect(sentenceFor(job({ state: 'done', pr: { number: 42, state: 'merged' } }))).toBe(
      'The agent finished: add a README line. Pull request 42 is merged.',
    );
    expect(sentenceFor(job({ state: 'failed', reason: 'The run was cancelled.' }))).toBe(
      'The agent failed: add a README line. The run was cancelled.',
    );
    expect(sentenceFor(job({ state: 'failed', stage: 'firewall' }))).toContain('It stopped at firewall.');
  });
});
