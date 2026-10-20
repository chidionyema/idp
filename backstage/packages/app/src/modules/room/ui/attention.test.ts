import { createElement } from 'react';
import { render, waitFor } from '@testing-library/react';
import ClaimsPanel from './ClaimsPanel';
import { board, clear, isLive, noteSeen, unreadable, ADVISORY_TTL_MS, type Signal } from './attention';
import { claimsSignal } from './ClaimsPanel';
import { keysSignal } from './KeySync';
import { harvSignal, STALE_S } from './HarvPanel';
import { researchSignal } from './ResearchFindings';
import { jobsSignal, type Job } from './AgentJobs';
import { conciergeSignal, type Task } from './ConciergeTasks';
import { laneSignal } from './GreenlaneHud';

const sig = (source: string, tier: Signal['tier'], summary = `${source} · x`): Signal => ({
  source,
  tier,
  summary,
});

describe('board', () => {
  it('is all quiet when every panel is clear', () => {
    const b = board([clear('a'), clear('b')], {}, 0);
    expect(b.shown).toEqual([]);
    expect(b.more).toBe(0);
    expect(b.worst).toBe('clear');
    expect(b.line).toBe('All quiet.');
  });

  it('shows worst first, caps at three, and counts the rest', () => {
    const list = [
      sig('a', 'advisory'),
      sig('b', 'caution'),
      sig('c', 'warning'),
      sig('d', 'caution'),
      sig('e', 'warning'),
      clear('f'),
    ];
    const b = board(list, noteSeen({}, list, 0), 0);
    expect(b.shown.map(s => s.source)).toEqual(['c', 'e', 'b']);
    expect(b.more).toBe(2);
    expect(b.worst).toBe('warning');
    expect(b.loud).toEqual(new Set(['a', 'b', 'c', 'd', 'e']));
    expect(b.line).toMatch(/^5 need you: c · x; e · x; b · x; and 2 more\.$/);
  });

  it('expires an unchanged advisory but never a caution or warning', () => {
    const list = [sig('a', 'advisory'), sig('b', 'caution')];
    const seen = noteSeen({}, list, 0);
    const later = ADVISORY_TTL_MS + 1;
    expect(isLive(list[0], seen, later)).toBe(false);
    expect(isLive(list[1], seen, later)).toBe(true);
    expect(board(list, seen, later).shown.map(s => s.source)).toEqual(['b']);
  });

  it('restarts an advisory clock when its words change', () => {
    const seen0 = noteSeen({}, [sig('a', 'advisory', 'one')], 0);
    const seen1 = noteSeen(seen0, [sig('a', 'advisory', 'two')], ADVISORY_TTL_MS);
    expect(seen1.a.since).toBe(ADVISORY_TTL_MS);
    expect(isLive(sig('a', 'advisory', 'two'), seen1, ADVISORY_TTL_MS + 10)).toBe(true);
  });

  it('treats an unreadable source as a caution, never clear', () => {
    expect(unreadable('keys').tier).toBe('caution');
  });
});

describe('panel signals', () => {
  it('claims: stale heartbeats are a caution; live claims are quiet', () => {
    expect(claimsSignal({ available: true, claims: [], counts: { live: 3 } } as any, null).tier).toBe('clear');
    expect(claimsSignal({ available: true, claims: [], counts: { live: 3, stale: 2 } } as any, null)).toEqual({
      source: 'claims',
      tier: 'caution',
      summary: 'claims · 2 stale heartbeats',
    });
    expect(claimsSignal(null, 'boom').tier).toBe('caution');
  });

  it('keys: a missing key is a warning, a failing bridge a caution', () => {
    const ok = { available: true, rows: [], counts: { synced: 4 } } as any;
    expect(keysSignal(ok, null).tier).toBe('clear');
    expect(keysSignal({ ...ok, counts: { synced: 3, missing: 1 } }, null).tier).toBe('warning');
    expect(keysSignal({ ...ok, counts: { synced: 3, failing: 1 } }, null).tier).toBe('caution');
  });

  it('harv: a day-old run is only an advisory', () => {
    const now = 10 * STALE_S;
    expect(harvSignal({ available: true, run_at: now - 60 }, null, now).tier).toBe('clear');
    expect(harvSignal({ available: true, run_at: now - STALE_S - 1 }, null, now).tier).toBe('advisory');
  });

  it('research: content is never an alarm; unreachable is an advisory', () => {
    expect(researchSignal({ available: true, claims: [] }, null).tier).toBe('clear');
    expect(researchSignal(null, 'down').tier).toBe('advisory');
  });

  it('jobs: a failed job is a caution with its reason', () => {
    const failed: Job = {
      run_id: 1,
      harness: 'pi',
      task: 't',
      run_url: null,
      stage: 'firewall',
      state: 'failed',
      reason: 'firewall refused',
      pr: null,
    };
    expect(jobsSignal([{ ...failed, state: 'running' }], null).tier).toBe('clear');
    expect(jobsSignal([failed], null)).toEqual({
      source: 'jobs',
      tier: 'caution',
      summary: 'jobs · 1 failed — firewall refused',
    });
  });

  it('concierge: a held task is a warning, it is waiting on the founder', () => {
    const t = { task_id: '1', goal: 'g', state: 'held', summary: 'pay step', last: '', outcome: '' } as Task;
    expect(conciergeSignal([t], null).tier).toBe('warning');
    expect(conciergeSignal([{ ...t, state: 'done' }], null).tier).toBe('clear');
  });

  it('lanes: main red is a warning; a quiet brief is clear', () => {
    const brief = {
      loud: false,
      summary: '',
      landing: null,
      waiting: 0,
      stuck: [],
      red: [],
      main_red: [],
      work_lost: 0,
    };
    expect(laneSignal({ available: true, brief }, null).tier).toBe('clear');
    expect(laneSignal({ available: true, brief: { ...brief, loud: true, main_red: ['ci'] } }, null)).toEqual({
      source: 'lanes',
      tier: 'warning',
      summary: 'lanes · main red',
    });
  });
});

describe('a mounted panel reports to the rail', () => {
  it('ClaimsPanel calls onSignal with its tier once its board is read', async () => {
    const onSignal = jest.fn();
    const call = async () =>
      ({
        ok: true,
        status: 200,
        json: async () => ({ available: true, claims: [], counts: { live: 1, stale: 1 } }),
      }) as unknown as Response;
    render(createElement(ClaimsPanel, { call, onSignal, pollMs: 60_000 }));
    await waitFor(() =>
      expect(onSignal).toHaveBeenLastCalledWith({
        source: 'claims',
        tier: 'caution',
        summary: 'claims · 1 stale heartbeat',
      }),
    );
  });
});
