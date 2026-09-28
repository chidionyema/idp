// The estate inventory tile's data (crew#740): what every plane the estate runs on actually
// holds, read from its own control plane and graded against git, as bin/idp-inventory writes
// docs/inventory.json on the state branch. Pure: no fetch here.
export type PlaneRead = 'yes' | 'PARTIAL' | 'UNKNOWN';
export type PlaneCounts = {
  MANAGED: number;
  DRIFTED: number;
  ORPHAN: number;
  GHOST: number;
  read: PlaneRead;
};
export type InventoryData = {
  generated_at: string;
  counts: Record<string, PlaneCounts>;
  blind: string[];
};

/** The path under the estate-state proxy; the inventory workflow publishes it there. */
export const INVENTORY_JSON = '/estate-state/docs/inventory.json';
/** The full table, on the same branch. */
export const INVENTORY_TABLE = '/estate-state/docs/inventory.md';

export const PLANE_WORD: Record<string, string> = {
  oci: 'Cloud tenancy',
  kubernetes: 'Cluster',
  github: 'GitHub',
  cloudflare: 'Cloudflare',
  tailscale: 'Tailscale',
  mac: 'Mac',
};

const VERDICTS = ['MANAGED', 'DRIFTED', 'ORPHAN', 'GHOST'] as const;

export const parseInventory = (raw: unknown): InventoryData => {
  const o = (raw ?? {}) as Partial<InventoryData>;
  if (!o.generated_at || typeof o.counts !== 'object' || o.counts === null)
    throw new Error('inventory.json is not the shape idp-inventory writes');
  const counts: Record<string, PlaneCounts> = {};
  for (const [plane, c] of Object.entries(o.counts)) {
    const row = (c ?? {}) as Partial<PlaneCounts> & { UNKNOWN?: boolean };
    const read: PlaneRead =
      row.read === 'PARTIAL' || row.read === 'UNKNOWN'
        ? row.read
        : row.UNKNOWN
        ? 'UNKNOWN'
        : 'yes';
    const n = (k: (typeof VERDICTS)[number]) =>
      typeof row[k] === 'number' ? (row[k] as number) : 0;
    counts[plane] = {
      MANAGED: n('MANAGED'),
      DRIFTED: n('DRIFTED'),
      ORPHAN: n('ORPHAN'),
      GHOST: n('GHOST'),
      read,
    };
  }
  return {
    generated_at: o.generated_at,
    counts,
    blind: Array.isArray(o.blind) ? o.blind.map(String) : [],
  };
};

/** Planes that hold something not as git says, worst first: unread, then red, then clean. */
export const planeOrder = (d: InventoryData) =>
  Object.keys(d.counts).sort((a, b) => rank(d.counts[b]) - rank(d.counts[a]));

const rank = (c: PlaneCounts) =>
  c.read === 'UNKNOWN'
    ? 3
    : c.DRIFTED + c.ORPHAN + c.GHOST > 0
    ? 2
    : c.read === 'PARTIAL'
    ? 1
    : 0;

export const planeSentence = (c: PlaneCounts) => {
  if (c.read === 'UNKNOWN')
    return 'could not be read, so what it holds is unknown';
  const red = c.DRIFTED + c.ORPHAN + c.GHOST;
  const parts = [`${c.MANAGED} managed`];
  if (c.DRIFTED) parts.push(`${c.DRIFTED} drifted`);
  if (c.ORPHAN) parts.push(`${c.ORPHAN} orphan${c.ORPHAN === 1 ? '' : 's'}`);
  if (c.GHOST) parts.push(`${c.GHOST} ghost${c.GHOST === 1 ? '' : 's'}`);
  const tail = c.read === 'PARTIAL' ? ' (part of it was not read)' : '';
  return `${parts.join(', ')}${
    red === 0 && !tail ? ', nothing outside git' : ''
  }${tail}`;
};

export const inventorySentence = (d: InventoryData) => {
  const planes = Object.values(d.counts);
  if (planes.length === 0)
    return 'No plane was read, so nothing here is known.';
  const unread = planes.filter(c => c.read === 'UNKNOWN').length;
  const red = planes.reduce((n, c) => n + c.DRIFTED + c.ORPHAN + c.GHOST, 0);
  const partial = planes.filter(c => c.read === 'PARTIAL').length;
  const bits: string[] = [];
  if (red === 0 && unread === 0 && partial === 0)
    return `Everything found on ${planes.length} plane${
      planes.length === 1 ? '' : 's'
    } is what git declares.`;
  if (red > 0) bits.push(`${red} thing${red === 1 ? '' : 's'} not as git says`);
  if (unread > 0)
    bits.push(`${unread} plane${unread === 1 ? '' : 's'} could not be read`);
  if (partial > 0)
    bits.push(`${partial} plane${partial === 1 ? '' : 's'} only partly read`);
  return `${bits.join('; ')}.`;
};
