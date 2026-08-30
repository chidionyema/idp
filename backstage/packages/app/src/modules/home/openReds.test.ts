import { Entity } from '@backstage/catalog-model';
import {
  drillSummary,
  drillsSentence,
  ownerName,
  redsFromAlerts,
  redsFromEntities,
  redsSentence,
  sortReds,
} from './openReds';

const NOW = Date.parse('2026-08-30T03:00:00Z');
const drill = (
  name: string,
  ann: Record<string, string>,
  tags: string[] = [],
  owner = 'group:default/platform',
): Entity => ({
  apiVersion: 'backstage.io/v1alpha1',
  kind: 'Resource',
  metadata: { name, annotations: ann, tags },
  spec: { type: 'drill', owner },
});
const door = (
  name: string,
  ann: Record<string, string>,
  owner?: string,
): Entity => ({
  apiVersion: 'backstage.io/v1alpha1',
  kind: 'Component',
  metadata: {
    name,
    annotations: ann,
    links: [{ url: 'https://crew/issues/1', title: 'Board item' }],
  },
  spec: { type: 'founder-surface', owner },
});

describe('open reds', () => {
  it('reads a firing alert with its owner label, start time, runbook and board', () => {
    const [r] = redsFromAlerts([
      {
        labels: {
          alertname: 'OttoDown',
          severity: 'critical',
          owner: 'idp-lane',
        },
        annotations: {
          summary: 'Otto has no running pod',
          runbook_url: 'https://runbook/otto',
          board: 'https://crew/issues/561',
        },
        startsAt: '2026-08-30T02:00:00Z',
        status: { state: 'active' },
      },
      { labels: { alertname: 'Old' }, status: { state: 'suppressed' } },
    ]);
    expect(r).toMatchObject({
      kind: 'alert',
      name: 'OttoDown',
      why: 'Otto has no running pod',
      owner: 'idp-lane',
      since: '2026-08-30T02:00:00Z',
      nextAction: 'Open the runbook',
      boardUrl: 'https://crew/issues/561',
      link: 'https://runbook/otto',
    });
    expect(redsFromAlerts([{ labels: { alertname: 'X' } }])[0]).toMatchObject({
      owner: undefined,
      nextAction: 'Name an owner and a next action on the rule',
    });
  });

  it('a drill never run, failed or stale is a red; a green one is not', () => {
    const reds = redsFromEntities(
      [
        drill('never', {}, ['never-run']),
        drill('failed', { 'last-status': 'failure', 'age-h': '5' }),
        drill(
          'stale',
          { 'last-status': 'success', 'age-h': '80', 'max-age-days': '1' },
          ['stale'],
        ),
        drill('green', { 'last-status': 'success', 'age-h': '3' }),
      ],
      NOW,
    );
    expect(reds.map(r => `${r.name}:${r.why}`)).toEqual([
      'never:Never run',
      'failed:Last run failure',
      'stale:Last green 80h ago, must run every 1 days',
    ]);
    expect(reds[1].since).toBe('2026-08-29T22:00:00.000Z');
    expect(reds[1].owner).toBe('platform');
  });

  it('a door down or not checked lately is a red with its board link; an up door is not', () => {
    const reds = redsFromEntities(
      [
        door('down', {
          'estate/health': 'FAIL 503',
          'estate/health-checked-at': '2026-08-30T02:50:00Z',
        }),
        door(
          'stale',
          {
            'estate/health': 'OK',
            'estate/health-checked-at': '2026-08-29T02:50:00Z',
          },
          'group:default/watch',
        ),
        door('up', {
          'estate/health': 'OK',
          'estate/health-checked-at': '2026-08-30T02:55:00Z',
        }),
      ],
      NOW,
    );
    expect(reds.map(r => `${r.name}:${r.why}:${r.owner ?? '-'}`)).toEqual([
      'down:FAIL 503:-',
      'stale:Not checked lately:watch',
    ]);
    expect(reds[0].boardUrl).toBe('https://crew/issues/1');
  });

  it('sorts the unowned first, then the oldest, and says the numbers', () => {
    const sorted = sortReds([
      {
        key: 'a',
        kind: 'alert',
        name: 'a',
        why: '',
        owner: 'x',
        since: '2026-08-30T01:00:00Z',
        nextAction: '',
      },
      {
        key: 'b',
        kind: 'alert',
        name: 'b',
        why: '',
        since: '2026-08-30T02:00:00Z',
        nextAction: '',
      },
      {
        key: 'c',
        kind: 'alert',
        name: 'c',
        why: '',
        since: '2026-08-30T00:30:00Z',
        nextAction: '',
      },
    ]);
    expect(sorted.map(r => r.key)).toEqual(['c', 'b', 'a']);
    expect(redsSentence(sorted)).toBe('3 reds open, 2 with no owner.');
    expect(redsSentence([sorted[2]])).toBe(
      '1 red open, every one with an owner.',
    );
    expect(redsSentence([])).toBe('No reds open.');
    expect(ownerName('group:default/platform')).toBe('platform');
    expect(ownerName('  ')).toBeUndefined();
  });

  it('counts every drill for the drills row and is blind with none (crew#684 CP5)', () => {
    const drill = (name: string, last: string) =>
      ({
        kind: 'Resource',
        metadata: { name, annotations: { 'last-status': last } },
        spec: { type: 'drill', owner: 'group:default/watch' },
      } as any);
    const d = drillSummary([
      drill('a', 'passed'),
      drill('b', 'failed'),
      drill('c', 'passed'),
    ]);
    expect(d).toEqual({ total: 3, green: 2, red: 1 });
    expect(drillsSentence(d)).toBe('2 of 3 drills green; 1 red, listed below.');
    expect(drillsSentence(drillSummary([]))).toBe(
      'No drills are in the catalogue, so nothing is rehearsed.',
    );
  });
});
