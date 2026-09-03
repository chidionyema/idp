// What the Tools page knows, with no React in it (crew#684 CP0, founder 2026-08-30: "all the
// tools one place ... another page in backstage just pure tools"; founder 2026-09-02 on the
// 49-tile page: "not intuitive, I don't know what I'm looking at ... it's not a maze").
//
// A tool is a `founder-surface` Component in the catalogue. Its tile is its `links:`, its group
// is its `estate/group` annotation (the crew#401 gate refuses a surface with no group), and it
// sits first inside its group when its `estate/tier` annotation says `daily`.
// Nothing here names a host or a tool: the catalogue is the list. A new service adds its door to
// backstage/founder/catalog-info.yaml and appears here without touching this page. The group
// names and the one line under each heading are the only copy this file owns.
import { Entity } from '@backstage/catalog-model';
import { byTitle } from './estate';

export const GROUP_ANNOTATION = 'estate/group';
export const TIER_ANNOTATION = 'estate/tier';
/** The `estate/tier` value that marks an everyday tool; those sit first inside their group. */
export const DAILY = 'daily';
/** The group a surface lands in when its annotation is blank; named so a stranger can read it. */
export const UNGROUPED = 'Other';

/** Groups in the order a person reads them; any other group follows alphabetically. */
export const GROUP_ORDER = [
  'See what is running',
  'Fix something',
  'AI and models',
  'Our products',
  'Money',
  'Build and ship',
  'Under the hood',
] as const;

/** Groups rendered folded (closed by default) because a person rarely opens them. */
export const FOLDED_GROUPS: readonly string[] = ['Under the hood'];

/** One plain line under each group heading saying what the group is for. Every GROUP_ORDER name has one; UNGROUPED too. */
export const GROUP_BLURB: Record<string, string> = {
  'See what is running': 'Dashboards, alerts and health. Start here when something looks wrong.',
  'Fix something': 'Logs, traces, pipelines and the cluster. Go here to find out why and put it right.',
  'AI and models': 'The models we call, what each call cost, and the agents that use them.',
  'Our products': 'The things we sell, as a customer sees them.',
  Money: 'What the estate costs and what customers pay.',
  'Build and ship': 'Code, reviews, builds and releases.',
  'Under the hood': 'Platform plumbing you rarely open: identity, secrets, networking and the cluster itself.',
  [UNGROUPED]: 'Tools whose catalogue entry has not said which group they belong to yet.',
};

export const HEADLINE = 'Every tool in the estate, one login.';
export const LEAD =
  'Press Open on a tile and it opens on your estate login. The everyday tools come first; platform plumbing is folded at the bottom.';

export type ToolGroup = { name: string; tools: Entity[]; folded: boolean };

const annotation = (e: Entity, key: string): string =>
  ((e.metadata.annotations ?? {})[key] ?? '').trim();

export const groupOf = (e: Entity): string => annotation(e, GROUP_ANNOTATION) || UNGROUPED;

/** True when the catalogue marks the tool as one a person opens most days. */
export const isDaily = (e: Entity): boolean =>
  annotation(e, TIER_ANNOTATION).toLowerCase() === DAILY;

const groupRank = (g: string) => {
  const i = (GROUP_ORDER as readonly string[]).indexOf(g);
  return i === -1 ? GROUP_ORDER.length : i;
};

/** Daily tools first, then by title; a stable sort keeps two daily tools in title order too. */
const byDailyThenTitle = (a: Entity, b: Entity) =>
  Number(isDaily(b)) - Number(isDaily(a)) || byTitle(a, b);

/**
 * Every surface, in its group. Groups come in GROUP_ORDER then A–Z; inside a group the daily
 * tools sit first, then the rest, each run in title order. A group is folded when its name is
 * in FOLDED_GROUPS.
 */
export const groupTools = (doors: Entity[]): ToolGroup[] => {
  const m = new Map<string, Entity[]>();
  for (const e of doors) {
    const g = groupOf(e);
    m.set(g, [...(m.get(g) ?? []), e]);
  }
  return [...m.entries()]
    .map(([name, tools]) => ({
      name,
      tools: [...tools].sort(byDailyThenTitle),
      folded: FOLDED_GROUPS.includes(name),
    }))
    .sort(
      (a, b) =>
        groupRank(a.name) - groupRank(b.name) || a.name.localeCompare(b.name),
    );
};

type Link = { title: string; url: string };

const links = (e: Entity): Link[] =>
  (e.metadata.links ?? [])
    .filter(l => typeof l.url === 'string' && l.url.trim() !== '')
    .map(l => ({ url: l.url, title: (l.title ?? '').trim() || 'Open' }));

/** The tile's button: the first catalogue link, titled 'Open' when the catalogue gave it no title. */
export const openLink = (e: Entity): Link | undefined => links(e)[0];

/** Every catalogue link after the first, for the small print under the button. */
export const moreLinks = (e: Entity): Link[] => links(e).slice(1);

const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

/**
 * The first sentence on the page: how many tools, in how many groups, how many sit first as
 * everyday tools and how many are folded away, never a bare number. It keeps the crew#718
 * caveat: one door still asks for a second credential, so the page may not promise the estate
 * login for every door.
 */
export const toolsSentence = (groups: ToolGroup[]): string => {
  const n = groups.reduce((s, g) => s + g.tools.length, 0);
  if (n === 0) {
    return 'No tools are registered yet; they appear here on their own once a sign-in page is listed.';
  }
  const daily = groups.reduce((s, g) => s + g.tools.filter(isDaily).length, 0);
  const folded = groups.filter(g => g.folded);
  const foldedCount = folded.reduce((s, g) => s + g.tools.length, 0);
  const parts = [`${plural(n, 'tool', 'tools')} in ${plural(groups.length, 'group', 'groups')}.`];
  const middle: string[] = [];
  if (daily > 0) {
    middle.push(`${daily} ${daily === 1 ? 'is an everyday tool and sits' : 'are everyday tools and sit'} first`);
  }
  if (foldedCount > 0) {
    const under = folded.map(g => g.name).join(' and ');
    middle.push(`${foldedCount} ${foldedCount === 1 ? 'is' : 'are'} plumbing, folded under ${under}`);
  }
  if (middle.length > 0) parts.push(`${middle.join('; ')}.`);
  parts.push(
    'Each opens on your estate login, unless its tile says it asks for a second credential.',
  );
  return parts.join(' ');
};
