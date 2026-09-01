// The Reports page's data (crew#684, founder 2026-09-01: "can we automate all reports, need report
// tab in Backstage"). docs/reports/index.json on the state branch is written by the publishing
// jobs (estate-state.yml every 15 minutes, estate-inventory.yml once a day) from the meta
// fragments bin/idp-reports-render emits; the page reads, dates and shows, and computes nothing.
import { State } from '../theme/tokens';

export const REPORTS_INDEX = '/estate-state/docs/reports/index.json';
/** A report's `file` (for example docs/reports/flux-state.md) is served under this proxy path. */
export const REPORTS_BASE = '/estate-state/';

export type Report = {
  id: string;
  title: string;
  file: string;
  generatedAt?: string;
  scheduleMinutes: number;
  summary: string;
  source?: string;
  /** The writer could not read its source; the report says so instead of showing a table. */
  blind: boolean;
};

export const parseReports = (raw: unknown): Report[] => {
  const list = (raw as { reports?: unknown } | undefined)?.reports;
  if (!Array.isArray(list)) return [];
  return list.flatMap(r => {
    const o = (r ?? {}) as Record<string, unknown>;
    if (typeof o.id !== 'string' || typeof o.file !== 'string') return [];
    return [
      {
        id: o.id,
        title: typeof o.title === 'string' ? o.title : o.id,
        file: o.file,
        generatedAt:
          typeof o.generated_at === 'string' ? o.generated_at : undefined,
        scheduleMinutes:
          typeof o.schedule_minutes === 'number' && o.schedule_minutes > 0
            ? o.schedule_minutes
            : 1440,
        summary: typeof o.summary === 'string' ? o.summary : '',
        source: typeof o.source === 'string' ? o.source : undefined,
        blind: o.blind === true,
      },
    ];
  });
};

export type Freshness = 'fresh' | 'stale' | 'never';

/** Late is twice the schedule: a 15-minute report is stale after 30 minutes. */
export const freshness = (r: Report, now: number): Freshness => {
  if (!r.generatedAt) return 'never';
  const t = Date.parse(r.generatedAt);
  if (Number.isNaN(t)) return 'never';
  return now - t > 2 * r.scheduleMinutes * 60_000 ? 'stale' : 'fresh';
};

export const FRESHNESS_WORD: Record<Freshness, string> = {
  fresh: 'Fresh',
  stale: 'Late',
  never: 'Never produced',
};

export const freshnessState = (r: Report, now: number): State => {
  if (r.blind) return 'blind';
  const f = freshness(r, now);
  if (f === 'fresh') return 'good';
  return f === 'stale' ? 'red' : 'blind';
};

export const everySentence = (minutes: number): string => {
  if (minutes % 1440 === 0) {
    return minutes === 1440 ? 'once a day' : `every ${minutes / 1440} days`;
  }
  if (minutes % 60 === 0) {
    return minutes === 60 ? 'every hour' : `every ${minutes / 60} hours`;
  }
  return `every ${minutes} minutes`;
};

export const reportsSentence = (reports: Report[], now: number): string => {
  if (reports.length === 0) return 'No reports have been published yet.';
  const c: Record<Freshness, number> = { fresh: 0, stale: 0, never: 0 };
  reports.forEach(r => {
    c[freshness(r, now)] += 1;
  });
  const blind = reports.filter(r => r.blind).length;
  const parts = [
    `${reports.length} ${reports.length === 1 ? 'report' : 'reports'}`,
    `${c.fresh} fresh`,
  ];
  if (c.stale) parts.push(`${c.stale} late`);
  if (c.never) parts.push(`${c.never} never produced`);
  if (blind) parts.push(`${blind} blind`);
  return `${parts.join(', ')}.`;
};
