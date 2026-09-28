// The Healthchecks tile (crew#684 CP5). Founder: "I need to see everything". Every cron-watched
// job the estate enrols in Healthchecks, counted by the states the vendor's API returns
// (https://healthchecks.io/docs/api/ "List existing checks": new, up, grace, down, paused), and
// every check that is not up named with its state. Read through the backend proxy
// (app-config.container.yaml proxy.endpoints./healthchecks) with a read-only key the backend
// holds; the page names no host and no key.

export const HC_CHECKS = '/healthchecks/checks/';

export type CheckStatus = 'new' | 'up' | 'grace' | 'down' | 'paused';
export const CHECK_STATUSES: CheckStatus[] = [
  'down',
  'grace',
  'new',
  'paused',
  'up',
];

export type Check = {
  name: string;
  status: CheckStatus;
  lastPing?: string;
  tags: string;
};

export type Checks = { checks: Check[]; unknown: number };

const isStatus = (s: unknown): s is CheckStatus =>
  typeof s === 'string' && (CHECK_STATUSES as string[]).includes(s);

/** The vendor's `{ checks: [...] }` document; a row with a status the vendor does not name counts as unknown. */
export const parseChecks = (doc: unknown): Checks => {
  const rows = (doc as { checks?: unknown } | null)?.checks;
  if (!Array.isArray(rows))
    throw new Error('Healthchecks answered without a checks list');
  const checks: Check[] = [];
  let unknown = 0;
  for (const r of rows) {
    const row = (r ?? {}) as Record<string, unknown>;
    if (!isStatus(row.status)) {
      unknown += 1;
      continue;
    }
    checks.push({
      name: String(row.name ?? row.slug ?? '(unnamed)'),
      status: row.status,
      lastPing: typeof row.last_ping === 'string' ? row.last_ping : undefined,
      tags: String(row.tags ?? ''),
    });
  }
  return { checks, unknown };
};

export const countBy = (c: Checks): Record<CheckStatus, number> => {
  const out = { new: 0, up: 0, grace: 0, down: 0, paused: 0 };
  for (const x of c.checks) out[x.status] += 1;
  return out;
};

/** Numbers with their denominators; an empty list is a blind tile, never a green one. */
export const checksSentence = (c: Checks): string => {
  const total = c.checks.length + c.unknown;
  if (total === 0) return 'No checks are enrolled, so nothing is watched.';
  const n = countBy(c);
  const parts = [`${n.up} of ${total} up`];
  if (n.down) parts.push(`${n.down} down`);
  if (n.grace) parts.push(`${n.grace} late`);
  if (n.new) parts.push(`${n.new} never pinged`);
  if (n.paused) parts.push(`${n.paused} paused`);
  if (c.unknown) parts.push(`${c.unknown} in a state this page does not know`);
  return `${parts.join(', ')}.`;
};

/** Down first, then late, then never pinged, then paused; up is not listed. */
export const notUp = (c: Checks): Check[] =>
  c.checks
    .filter(x => x.status !== 'up')
    .sort(
      (a, b) =>
        CHECK_STATUSES.indexOf(a.status) - CHECK_STATUSES.indexOf(b.status) ||
        a.name.localeCompare(b.name),
    );

export const STATUS_WORD: Record<CheckStatus, string> = {
  down: 'Down',
  grace: 'Late',
  new: 'Never pinged',
  paused: 'Paused',
  up: 'Up',
};
