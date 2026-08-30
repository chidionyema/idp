// The open-reds table (crew#684 CP2). Founder: "every firing alert and red drill with Owner,
// Since, Next action, board link. A red with no owner is itself a red." Three sources, one
// shape: Alertmanager's active alerts, the catalogue's drill Resources and the catalogue's
// founder-surface doors. Nothing here decides who owns a red; it reads the owner the rule or
// the entity names and says plainly when there is none (CP3 makes the owner mandatory).
import { Entity } from '@backstage/catalog-model';
import { FOUNDER_SURFACE_TYPE, healthOf, needsYou, screenUrl } from './estate';

/** One alert as Alertmanager's `GET /api/v2/alerts` lists it. */
export type AlertmanagerAlert = {
  labels: Record<string, string>;
  annotations?: Record<string, string>;
  startsAt?: string;
  status?: { state?: string };
};

export type RedKind = 'alert' | 'drill' | 'door';

export type Red = {
  key: string;
  kind: RedKind;
  name: string;
  /** What is red, in the words the source gave. */
  why: string;
  /** The owner the rule or entity names; undefined is itself a red. */
  owner?: string;
  /** ISO time the red began, when the source says. */
  since?: string;
  nextAction: string;
  boardUrl?: string;
  /** Where to look: a runbook, the door, the entity. */
  link?: string;
};

export const DRILL_TYPE = 'drill';
const FAILED = new Set(['failure', 'failed', 'fail', 'cancelled', 'timed_out']);

/** "group:default/platform" -> "platform"; the founder reads names, not refs. */
export const ownerName = (ref: string | undefined): string | undefined => {
  const s = (ref ?? '').trim();
  if (!s) return undefined;
  return s.split('/').pop() || undefined;
};

const boardOf = (e: Entity): string | undefined =>
  e.metadata.annotations?.['estate/board'] ??
  (e.metadata.links ?? []).find(l => /board|issue|ticket/i.test(l.title ?? ''))
    ?.url;

export const redsFromAlerts = (alerts: AlertmanagerAlert[]): Red[] =>
  alerts
    .filter(a => (a.status?.state ?? 'active') === 'active')
    .map(a => {
      const l = a.labels ?? {};
      const an = a.annotations ?? {};
      const name = l.alertname ?? 'alert';
      const where = l.instance ?? l.route ?? l.namespace;
      return {
        key: `alert/${name}/${where ?? ''}`,
        kind: 'alert' as const,
        name: where ? `${name} ${where}` : name,
        why: an.summary ?? an.description ?? name,
        owner: ownerName(l.owner),
        since: a.startsAt,
        nextAction:
          an.next_action ??
          (an.runbook_url
            ? 'Open the runbook'
            : 'Name an owner and a next action on the rule'),
        boardUrl: an.board,
        link: an.runbook_url,
      };
    });

const drillWhy = (e: Entity): string | undefined => {
  const ann = e.metadata.annotations ?? {};
  const tags = e.metadata.tags ?? [];
  const last = String(ann['last-status'] ?? '').toLowerCase();
  if (tags.includes('never-run') || !last || last === 'never run')
    return 'Never run';
  if (FAILED.has(last)) return `Last run ${last}`;
  if (tags.includes('stale') || String(ann.stale) === 'true')
    return `Last green ${ann['age-h'] ?? '?'}h ago, must run every ${
      ann['max-age-days'] ?? '?'
    } days`;
  return undefined;
};

/** The drills row (crew#684 CP5): every drill Resource in the catalogue, counted. */
export type DrillSummary = { total: number; green: number; red: number };

export const drillSummary = (entities: Entity[]): DrillSummary => {
  let total = 0;
  let red = 0;
  for (const e of entities) {
    if (e.kind !== 'Resource' || String(e.spec?.type ?? '') !== DRILL_TYPE)
      continue;
    total += 1;
    if (drillWhy(e)) red += 1;
  }
  return { total, green: total - red, red };
};

/** Numbers with their denominator; no drills is a blind row, never a green one. */
export const drillsSentence = (d: DrillSummary): string =>
  d.total === 0
    ? 'No drills are in the catalogue, so nothing is rehearsed.'
    : `${d.green} of ${d.total} drills green; ${d.red} red, listed below.`;

export const redsFromEntities = (
  entities: Entity[],
  now: number = Date.now(),
): Red[] => {
  const reds: Red[] = [];
  for (const e of entities) {
    const type = String(e.spec?.type ?? '');
    const owner = ownerName(String(e.spec?.owner ?? ''));
    const ann = e.metadata.annotations ?? {};
    const name = e.metadata.title ?? e.metadata.name;
    if (e.kind === 'Resource' && type === DRILL_TYPE) {
      const why = drillWhy(e);
      if (!why) continue;
      const ageH = Number(ann['age-h']);
      reds.push({
        key: `drill/${e.metadata.name}`,
        kind: 'drill',
        name,
        why,
        owner,
        since: Number.isFinite(ageH)
          ? new Date(now - ageH * 3600 * 1000).toISOString()
          : undefined,
        nextAction: 'Run the drill and read its log',
        boardUrl: boardOf(e),
      });
    } else if (e.kind === 'Component' && type === FOUNDER_SURFACE_TYPE) {
      const h = healthOf(e, now);
      if (!needsYou(h)) continue;
      reds.push({
        key: `door/${e.metadata.name}`,
        kind: 'door',
        name,
        why:
          h === 'down' ? ann['estate/health'] ?? 'Down' : 'Not checked lately',
        owner,
        since: ann['estate/health-checked-at'],
        nextAction: 'Open the door and read the probe',
        boardUrl: boardOf(e),
        link: screenUrl(e),
      });
    }
  }
  return reds;
};

/** Unowned first (they are the reds nobody is on), then the oldest. */
export const sortReds = (reds: Red[]): Red[] =>
  [...reds].sort((a, b) => {
    const ao = a.owner ? 1 : 0;
    const bo = b.owner ? 1 : 0;
    if (ao !== bo) return ao - bo;
    const at = Date.parse(a.since ?? '') || Number.MAX_SAFE_INTEGER;
    const bt = Date.parse(b.since ?? '') || Number.MAX_SAFE_INTEGER;
    return at - bt;
  });

export const redsSentence = (reds: Red[]): string => {
  if (reds.length === 0) return 'No reds open.';
  const unowned = reds.filter(r => !r.owner).length;
  const n = reds.length === 1 ? '1 red open' : `${reds.length} reds open`;
  return unowned === 0
    ? `${n}, every one with an owner.`
    : `${n}, ${unowned} with no owner.`;
};
